"""Tipo TRASPASO, la salida (US-TRS-001, fase 5): almacén de origen -> EN_TRANSITO.

El traspaso tiene dos pasos (X-01): la salida (este tipo) y la recepción (`recepcion.py`). Entre
ambos la existencia está En tránsito y no cuenta para ningún almacén. El vale queda en estado
`EN_TRANSITO`, con `destino_almacen_id`, folio `CLAVE-TRS-000001` y QR (X-06). Quien envía firma
con su sesión (F-09).

Reglas: X-01 a X-04, X-06, X-07, X-09, F-09 (en `evaluador_traspasos.py` las que se evalúan).
Fuera de alcance: X-05 (aviso por mínimo, FEAT-004), X-14 (cancelar lo hace CANCELACION).

Traslado lateral (FEAT-015, X-16 a X-20): entre dos almacenes de tercer nivel la ruta la autoriza el
supervisor del origen. Si quien envía lo es, su envío es la autorización (X-16: amarillo y
observación); si no, el vale es naranja (X-17) y se confirma con `autorizacion_id` de tipo TRASLADO
(la valida el motor con `AutorizacionService.validar_traslado_para_vale`). Los avisos de X-20 (nadie
en el destino puede recibir) no bloquean. La push informativa al destino (X-20, reglas NT) la manda
el módulo `notificaciones` de FEAT-014 después del commit; mientras no exista, el punto de enganche
es `MovimientoService._confirmar_una_vez`, justo después del `commit`.

Cuerpo: `destino_almacen_id` y los renglones (código de la pieza, o del artículo y cantidad). No
lleva trabajador, ni credencial, ni condición, ni costos.

Mismo criterio que E-15 y E-16 de la entrega: una pieza repetida en el borrador se ignora y un
artículo por cantidad repetido suma.
"""

import uuid

from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.models import Almacen, EstadoAlmacen, UbicacionVirtual
from app.modulos.movimientos.cargador import hechos_de_articulo, hechos_de_pieza
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
    RutaEvaluada,
)
from app.modulos.movimientos.evaluador import Motivo
from app.modulos.movimientos.evaluador_minimos import regla_minimo
from app.modulos.movimientos.evaluador_traspasos import (
    ClaseRuta,
    HechosAlmacen,
    HechosRenglonTraspaso,
    QuienAutoriza,
    clasificar_ruta,
    evaluar_renglon_traspaso,
    regla_x03_ruta,
    regla_x16_envio_propio,
    regla_x17_con_autorizacion,
    regla_x18_lateral,
    regla_x20_sin_receptor,
)
from app.modulos.movimientos.exceptions import RutaSoloAdministrador
from app.modulos.movimientos.models import EstadoVale, FirmaModo, Nivel, TipoVale
from app.modulos.movimientos.repository_traspasos import TraspasoRepository
from app.modulos.movimientos.schemas import RenglonIn, ValeIn
from app.modulos.movimientos.tipos.base import (
    ManejadorTipo,
    motivos_ids,
    vista_articulo,
    vista_pieza,
    vista_titular,
)

# Reglas que cumple todo movimiento de una salida: dos pasos con la existencia En tránsito (X-01)
# y origen y destino guardados (X-07).
REGLAS_DE_LA_SALIDA = ["X-01", "X-07"]


def _campo(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


def hechos_de_almacen(almacen: Almacen) -> HechosAlmacen:
    return HechosAlmacen(
        id=almacen.id,
        clave=almacen.clave,
        nombre=almacen.nombre,
        padre_id=almacen.padre_id,
        activo=almacen.estado == EstadoAlmacen.ACTIVO,
        tipo=almacen.tipo,
    )


def _resumen_almacen(almacen: Almacen) -> dict[str, str]:
    return {"id": str(almacen.id), "clave": almacen.clave, "nombre": almacen.nombre}


def normalizar_renglones_de_traslado(ctx: ContextoVale, cuerpo: ValeIn) -> list[RenglonIn]:
    """Pieza repetida se ignora; artículo por cantidad repetido suma (como E-15 y E-16)."""
    salida: list[RenglonIn] = []
    piezas: set[uuid.UUID] = set()
    por_articulo: dict[uuid.UUID, int] = {}
    desconocidos: set[str] = set()
    for renglon in cuerpo.renglones:
        ident = ctx.cargador.identificar(renglon.codigo)
        if ident.tipo == "PIEZA" and ident.pieza is not None:
            if ident.pieza.id in piezas:
                continue
            piezas.add(ident.pieza.id)
            salida.append(renglon)
        elif ident.tipo == "ARTICULO" and ident.articulo and ident.articulo.control == "CANTIDAD":
            indice = por_articulo.get(ident.articulo.id)
            if indice is None:
                por_articulo[ident.articulo.id] = len(salida)
                salida.append(renglon)
            else:
                previo = salida[indice]
                salida[indice] = previo.model_copy(
                    update={"cantidad": previo.cantidad + renglon.cantidad}
                )
        else:
            clave = renglon.codigo.strip().casefold()
            if clave in desconocidos:
                continue
            desconocidos.add(clave)
            salida.append(renglon)
    return salida


class TraspasoTipo(ManejadorTipo):
    tipo = TipoVale.TRASPASO
    permiso = P.TRASPASOS_OPERAR
    firma_modo = FirmaModo.SESION  # F-09: firma quien envía, con su sesión

    # ------------------------------------------------------------------ validación

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        if cuerpo.destino_almacen_id is None:
            raise _campo("destino_almacen_id", "Elige a qué almacén se envía.")
        if cuerpo.trabajador_id is not None:
            raise _campo("trabajador_id", "Un traspaso no lleva trabajador.")
        if cuerpo.vale_origen_id is not None:
            raise _campo("vale_origen_id", "Un traspaso no se liga a otro vale.")
        for i, renglon in enumerate(cuerpo.renglones):
            if renglon.pieza is not None:
                raise _campo(f"renglones.{i}.pieza", "Los datos de pieza son solo de las entradas.")
        if confirmar and not cuerpo.renglones:
            raise _campo("renglones", "Agrega al menos un renglón.")

    def normalizar_renglones(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[RenglonIn]:
        return normalizar_renglones_de_traslado(ctx, cuerpo)

    def almacenes_involucrados(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[Almacen]:
        """AL-04: ni el origen ni el destino pueden estar cerrados."""
        almacenes = [ctx.almacen]
        if cuerpo.destino_almacen_id is not None:
            destino = ctx.session.get(Almacen, cuerpo.destino_almacen_id)
            if destino is not None:
                almacenes.append(destino)
        return almacenes

    # ------------------------------------------------------------------ evaluación

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        carga = ctx.cargador
        repo = TraspasoRepository(ctx.session)
        assert cuerpo.destino_almacen_id is not None
        evaluacion = Evaluacion()

        destino = repo.almacen(cuerpo.destino_almacen_id)
        if destino is None:
            evaluacion.motivos_vale = [
                Motivo("X-03", Nivel.ROJO, "El almacén de destino no existe.")
            ]
            evaluacion.ruta = RutaEvaluada(ClaseRuta.NO_HABITUAL, QuienAutoriza.NADIE)
        else:
            self._evaluar_ruta(ctx, evaluacion, destino)

        for numero, renglon in enumerate(cuerpo.renglones, start=1):
            ident = carga.identificar(renglon.codigo)
            articulo, pieza = ident.articulo, ident.pieza
            titular = None
            if pieza is not None and pieza.ubicacion_id != ctx.ubicacion_almacen.id:
                titular = carga.titular_de(pieza)
            existencia = carga.existencia(ctx.ubicacion_almacen.id, articulo.id) if articulo else 0
            hechos = HechosRenglonTraspaso(
                codigo=renglon.codigo,
                cantidad=renglon.cantidad,
                articulo=hechos_de_articulo(articulo) if articulo else None,
                pieza=hechos_de_pieza(pieza) if pieza else None,
                titular=titular,
                ubicacion_origen_id=ctx.ubicacion_almacen.id,
                existencia_origen=existencia,
            )
            motivos = evaluar_renglon_traspaso(hechos)
            if articulo is not None:
                previo = sum(
                    r.cantidad
                    for r in evaluacion.renglones
                    if r.articulo_id == articulo.id
                    and (r.pieza is None or r.pieza.get("estado") == "APTO")
                )
                salida_disponible = renglon.cantidad + previo
                if pieza is not None and pieza.estado != "APTO":
                    salida_disponible = previo
                aviso = regla_minimo(
                    "X-05",
                    carga.almacenes.minimo(ctx.ubicacion_almacen.id, articulo.id),
                    carga.disponible(ctx.ubicacion_almacen.id, articulo),
                    salida_disponible,
                )
                if aviso is not None:
                    motivos.append(aviso)
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=numero,
                    codigo=renglon.codigo,
                    cantidad=renglon.cantidad,
                    motivos=motivos,
                    articulo_id=articulo.id if articulo else None,
                    pieza_id=pieza.id if pieza else None,
                    articulo=vista_articulo(hechos.articulo) if hechos.articulo else None,
                    pieza=vista_pieza(hechos.pieza) if hechos.pieza else None,
                    titular=vista_titular(titular) if titular else None,
                    disponible=existencia if articulo else None,
                    extra={"observacion": renglon.observacion},
                )
            )
        return evaluacion

    def _evaluar_ruta(self, ctx: ContextoVale, evaluacion: Evaluacion, destino: Almacen) -> None:
        """X-03, X-16 a X-18 y X-20: la ruta del traspaso y quién la autoriza. Llena
        `motivos_vale`, `ruta` y las marcas que usa `exigir_al_confirmar`."""
        acceso = AccesoService(ctx.session)
        origen_h, destino_h = hechos_de_almacen(ctx.almacen), hechos_de_almacen(destino)
        clase = clasificar_ruta(origen_h, destino_h)
        # X-03: otra ruta que no es padre-hijo solo con `almacenes.todos`.
        puede_todos = acceso.puede_operar_todos_los_almacenes(ctx.usuario)
        motivos: list[Motivo] = []
        autorizadores = None

        if clase == ClaseRuta.LATERAL:
            motivos.append(regla_x18_lateral(origen_h, destino_h))  # X-18, antes que X-03
            if acceso.es_supervisor_de(ctx.usuario, ctx.almacen.id):
                autoriza = QuienAutoriza.ENVIO_PROPIO  # X-16: su envío es la autorización
                motivos.append(regla_x16_envio_propio(origen_h, destino_h))
                evaluacion.pide_observacion_vale = True
                evaluacion.datos["envio_propio"] = True
            elif puede_todos:  # un rol con `almacenes.todos` y sin `autorizaciones.resolver`
                autoriza = QuienAutoriza.ADMINISTRADOR
                motivos.append(regla_x03_ruta(origen_h, destino_h, puede_ruta_excepcional=True))
                self._marcar_ruta_no_habitual(ctx, evaluacion, destino, puede=True)
            else:  # X-17: hace falta una autorización de traslado
                autoriza = QuienAutoriza.SUPERVISOR_ORIGEN
                autorizadores = acceso.contar_con_permiso_en(
                    P.AUTORIZACIONES_RESOLVER,
                    ctx.almacen.id,
                    incluir_todos=True,
                    excluir_usuario_id=ctx.usuario.id,
                )
                motivos.append(regla_x17_con_autorizacion(origen_h, destino_h, autorizadores))
            receptores = acceso.contar_con_permiso_en(P.TRASPASOS_RECIBIR, destino.id)
            if (aviso := regla_x20_sin_receptor(destino_h, receptores)) is not None:
                motivos.append(aviso)
        else:
            motivos.append(regla_x03_ruta(origen_h, destino_h, puede_ruta_excepcional=puede_todos))
            autoriza = QuienAutoriza.NADIE
            if clase == ClaseRuta.NO_HABITUAL:
                self._marcar_ruta_no_habitual(ctx, evaluacion, destino, puede=puede_todos)
                if puede_todos:
                    autoriza = QuienAutoriza.ADMINISTRADOR
        evaluacion.motivos_vale = motivos
        evaluacion.ruta = RutaEvaluada(clase, autoriza, autorizadores)

    @staticmethod
    def _marcar_ruta_no_habitual(
        ctx: ContextoVale, evaluacion: Evaluacion, destino: Almacen, *, puede: bool
    ) -> None:
        evaluacion.datos["ruta_no_habitual"] = {
            "puede": puede,
            "origen": _resumen_almacen(ctx.almacen),
            "destino": _resumen_almacen(destino),
        }
        evaluacion.pide_observacion_vale = puede

    # ---------------------------------------------------------------- confirmación

    def exigir_al_confirmar(self, cuerpo: ValeIn, evaluacion: Evaluacion) -> None:
        """X-16: el envío propio de un traslado lateral pide la observación del motivo (422).
        X-03: una ruta que no es padre-hijo la confirma solo quien tiene `almacenes.todos`
        (403 `RUTA_SOLO_ADMINISTRADOR`) y con observación en el vale (422)."""
        if (
            evaluacion.datos.get("envio_propio")
            and not (getattr(cuerpo, "observacion", None) or "").strip()
        ):
            mensaje = "Escribe para qué se manda este traslado."
            raise DatosInvalidos(
                mensaje, [{"campo": "observacion", "mensaje": mensaje, "regla": "X-16"}]
            )
        ruta = evaluacion.datos.get("ruta_no_habitual")
        if ruta is None:
            return
        if not ruta["puede"]:
            raise RutaSoloAdministrador(
                detalles={"regla": "X-03", "origen": ruta["origen"], "destino": ruta["destino"]}
            )
        if not (getattr(cuerpo, "observacion", None) or "").strip():
            mensaje = "Anota por qué se envía por una ruta que no es la habitual."
            raise DatosInvalidos(
                mensaje, [{"campo": "observacion", "mensaje": mensaje, "regla": "X-03"}]
            )

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        carga = ctx.cargador
        plan = PlanBloqueo()
        en_transito = carga.ubicacion_virtual(UbicacionVirtual.EN_TRANSITO)
        for renglon in cuerpo.renglones:
            ident = carga.identificar(renglon.codigo)
            if ident.articulo is None:
                continue
            plan.existencias.add((ctx.ubicacion_almacen.id, ident.articulo.id))
            plan.existencias.add((en_transito.id, ident.articulo.id))
            if ident.pieza is not None:
                plan.piezas.add(ident.pieza.id)
        return plan

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        return DatosVale(
            destino_almacen_id=cuerpo.destino_almacen_id,
            estado=EstadoVale.EN_TRANSITO,  # X-06
            firma_modo=FirmaModo.SESION,
        )

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        en_transito = ctx.cargador.ubicacion_virtual(UbicacionVirtual.EN_TRANSITO)
        reglas_del_vale = [m.regla for m in evaluacion.motivos_vale]
        movimientos = []
        for r in evaluacion.renglones:
            assert r.articulo_id is not None
            reglas = list(REGLAS_DE_LA_SALIDA)
            for regla in [*reglas_del_vale, *motivos_ids(r)]:
                if regla not in reglas:
                    reglas.append(regla)
            movimientos.append(
                MovimientoNuevo(
                    renglon=r.renglon,
                    articulo_id=r.articulo_id,
                    pieza_id=r.pieza_id,
                    cantidad=r.cantidad,
                    origen_id=ctx.ubicacion_almacen.id,
                    destino_id=en_transito.id,  # X-01
                    condicion=None,  # la pieza conserva su estado (X-04)
                    nivel=r.nivel,
                    reglas=reglas,
                    observacion=r.extra.get("observacion"),
                )
            )
        return movimientos
