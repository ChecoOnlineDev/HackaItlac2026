"""Tipo RECEPCION y `GET /api/traspasos/por-recibir` (US-TRS-002, fase 5): EN_TRANSITO -> destino.

`vale_origen_id` es el traspaso. Quien recibe es el responsable de lo recibido (X-08) y firma con
su sesión (F-09). Folio `CLAVE-REC-000001` del almacén que recibe.

Reglas: X-08, X-10 a X-13, F-09, RG-05 (en `evaluador_traspasos.py` las que se evalúan).

Cómo se recibe (X-11): cada renglón es lo que se escaneó, con su cantidad. Para "recibir todo de
una vez" la interfaz manda todos los renglones pendientes del traspaso (los trae
`GET /api/traspasos/por-recibir`); para recibir "renglón por renglón", los que ya escaneó. Una
recepción sin renglones se rechaza.

Qué pasa con lo que falta (X-13), con recepciones sucesivas:
- Lo pendiente de un traspaso es lo enviado menos lo ya recibido en TODAS sus recepciones.
- Al confirmar una recepción, si queda algo pendiente, lo no recibido SIGUE En tránsito (el
  movimiento solo saca de EN_TRANSITO lo que llegó) y el traspaso original queda
  `RECIBIDO_CON_DIFERENCIAS`; si no queda nada, queda `RECIBIDO`.
- Un traspaso con diferencias puede recibirse otra vez (las veces que haga falta) hasta
  completarse; entonces pasa a `RECIBIDO`. Mientras tenga algo pendiente aparece en
  `por-recibir` y es la lista de revisión de X-13. Resolver lo que nunca llega (regresarlo al
  origen o darlo de baja) queda fuera de alcance.
- Una pieza o un artículo que ya se recibió no se vuelve a recibir (X-12, rojo), y no se recibe
  más cantidad de la que se envió.
"""

import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.cargador import hechos_de_articulo, hechos_de_pieza
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador_traspasos import (
    HechosRenglonRecepcion,
    estado_despues_de_recibir,
    regla_estado_del_traspaso,
    regla_rg14_observacion,
    regla_x10_destino,
    regla_x12_pertenece,
    regla_x13_diferencias,
)
from app.modulos.movimientos.exceptions import ValeNoEncontrado
from app.modulos.movimientos.models import FirmaModo, Nivel, TipoVale, Vale
from app.modulos.movimientos.repository_traspasos import (
    Clave,
    LineaTraspaso,
    TraspasoRepository,
)
from app.modulos.movimientos.schemas import AlmacenResumenOut, PersonaOut, RenglonIn, ValeIn
from app.modulos.movimientos.schemas_traspasos import (
    PorRecibirOut,
    RecepcionResumenOut,
    RenglonPorRecibirOut,
    TotalPorRecibirOut,
    TraspasoPorRecibirOut,
)
from app.modulos.movimientos.tipos.base import (
    ManejadorTipo,
    motivos_ids,
    vista_articulo,
    vista_pieza,
)
from app.modulos.movimientos.tipos.traspaso import (
    hechos_de_almacen,
    normalizar_renglones_de_traslado,
)

if TYPE_CHECKING:
    from app.modulos.movimientos.service import MovimientoService

# Reglas de todo movimiento de una recepción: quien recibe es el responsable (X-08) y solo el
# destino recibe (X-10).
REGLAS_DE_LA_RECEPCION = ["X-08", "X-10"]


def _campo(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


def _clave_de(ident) -> Clave | None:
    """A qué renglón de un traspaso corresponde lo escaneado: la pieza, o el artículo por
    cantidad."""
    if ident.pieza is not None:
        return (ident.pieza.articulo_id, ident.pieza.id)
    if ident.articulo is not None and ident.articulo.control == "CANTIDAD":
        return (ident.articulo.id, None)
    return None


class RecepcionTipo(ManejadorTipo):
    tipo = TipoVale.RECEPCION
    permiso = P.TRASPASOS_OPERAR
    firma_modo = FirmaModo.SESION  # F-09: firma quien recibe, con su sesión

    # ------------------------------------------------------------------ validación

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        if cuerpo.vale_origen_id is None:
            raise _campo("vale_origen_id", "Indica qué traspaso se recibe.")
        if cuerpo.trabajador_id is not None:
            raise _campo("trabajador_id", "Una recepción no lleva trabajador.")
        if cuerpo.destino_almacen_id is not None:
            raise _campo("destino_almacen_id", "El destino de una recepción es tu almacén.")
        for i, renglon in enumerate(cuerpo.renglones):
            if renglon.pieza is not None:
                raise _campo(f"renglones.{i}.pieza", "Los datos de pieza son solo de las entradas.")
        if confirmar and not cuerpo.renglones:
            raise _campo("renglones", "Escanea al menos un renglón o recibe todo el traspaso.")

    def normalizar_renglones(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[RenglonIn]:
        return normalizar_renglones_de_traslado(ctx, cuerpo)

    # ------------------------------------------------------------------ evaluación

    @staticmethod
    def _traspaso(repo: TraspasoRepository, vale_origen_id: uuid.UUID) -> Vale:
        traspaso = repo.vale(vale_origen_id)
        if traspaso is None:
            raise ValeNoEncontrado("No se encontró el traspaso.")
        if traspaso.tipo != TipoVale.TRASPASO or traspaso.destino_almacen_id is None:
            raise _campo("vale_origen_id", "Ese vale no es un traspaso.")
        return traspaso

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        assert cuerpo.vale_origen_id is not None
        carga = ctx.cargador
        repo = TraspasoRepository(ctx.session)
        traspaso = self._traspaso(repo, cuerpo.vale_origen_id)
        evaluacion = Evaluacion()

        destino = repo.almacen(traspaso.destino_almacen_id)
        assert destino is not None
        x10 = regla_x10_destino(hechos_de_almacen(destino), ctx.almacen.id, ctx.almacen.nombre)
        if x10 is not None:
            # Otro almacén no ve el contenido del traspaso: todo renglón queda en rojo.
            evaluacion.motivos_vale = [x10]
            for numero, renglon in enumerate(cuerpo.renglones, start=1):
                evaluacion.renglones.append(
                    RenglonEvaluado(
                        renglon=numero,
                        codigo=renglon.codigo,
                        cantidad=renglon.cantidad,
                        motivos=[x10],
                    )
                )
            return evaluacion

        estado = regla_estado_del_traspaso(traspaso.estado)
        if estado is not None:
            evaluacion.motivos_vale.append(estado)
        lineas: dict[Clave, LineaTraspaso] = {ln.clave: ln for ln in repo.lineas(traspaso.id)}
        pendiente_total = sum(ln.pendiente for ln in lineas.values())

        pedido: dict[uuid.UUID, int] = defaultdict(int)
        for numero, renglon in enumerate(cuerpo.renglones, start=1):
            ident = carga.identificar(renglon.codigo)
            articulo, pieza = ident.articulo, ident.pieza
            clave = _clave_de(ident)
            linea = lineas.get(clave) if clave else None
            hechos = HechosRenglonRecepcion(
                codigo=renglon.codigo,
                cantidad=renglon.cantidad,
                articulo=hechos_de_articulo(articulo) if articulo else None,
                pieza=hechos_de_pieza(pieza) if pieza else None,
                enviada=linea.enviada if linea else 0,
                recibida=linea.recibida if linea else 0,
                pedido_previo=pedido[articulo.id] if articulo and pieza is None else 0,
            )
            motivo = regla_x12_pertenece(hechos)
            if motivo is None and articulo is not None and pieza is None:
                pedido[articulo.id] += renglon.cantidad
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=numero,
                    codigo=renglon.codigo,
                    cantidad=renglon.cantidad,
                    motivos=[motivo] if motivo else [],
                    articulo_id=articulo.id if articulo else None,
                    pieza_id=pieza.id if pieza else None,
                    articulo=vista_articulo(hechos.articulo) if hechos.articulo else None,
                    pieza=vista_pieza(hechos.pieza) if hechos.pieza else None,
                    # Lo que todavía falta por recibir de este renglón.
                    disponible=hechos.pendiente if articulo else None,
                    extra={"observacion": renglon.observacion},
                )
            )

        recibido_ahora = sum(r.cantidad for r in evaluacion.renglones if r.nivel != Nivel.ROJO)
        if recibido_ahora > 0:
            x13 = regla_x13_diferencias(pendiente_total - recibido_ahora)
            if x13 is not None:
                evaluacion.motivos_vale.append(x13)
            # RG-14: con diferencias, la observación es obligatoria (rojo hasta que se escriba).
            rg14 = regla_rg14_observacion(
                pendiente_total - recibido_ahora, getattr(cuerpo, "observacion", None)
            )
            if rg14 is not None:
                evaluacion.motivos_vale.append(rg14)
        return evaluacion

    def exigir_al_confirmar(self, cuerpo: ValeIn, evaluacion: Evaluacion) -> None:
        """RG-14: una recepción con diferencias sin observación es un 422 sobre ese campo."""
        for motivo in evaluacion.motivos_vale:
            if motivo.regla == "RG-14":
                raise DatosInvalidos(
                    motivo.mensaje,
                    [{"campo": "observacion", "mensaje": motivo.mensaje, "regla": "RG-14"}],
                )

    # ---------------------------------------------------------------- confirmación

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        assert cuerpo.vale_origen_id is not None
        carga = ctx.cargador
        traspaso = self._traspaso(TraspasoRepository(ctx.session), cuerpo.vale_origen_id)
        # Primero el traspaso: dos recepciones del mismo traspaso se turnan aquí, y la segunda
        # vuelve a evaluar con lo que la primera ya recibió.
        plan = PlanBloqueo(vales={traspaso.id})
        en_transito = carga.ubicacion_virtual(UbicacionVirtual.EN_TRANSITO)
        for renglon in cuerpo.renglones:
            ident = carga.identificar(renglon.codigo)
            if ident.articulo is None:
                continue
            plan.existencias.add((en_transito.id, ident.articulo.id))
            plan.existencias.add((ctx.ubicacion_almacen.id, ident.articulo.id))
            if ident.pieza is not None:
                plan.piezas.add(ident.pieza.id)
        return plan

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        return DatosVale(vale_origen_id=cuerpo.vale_origen_id, firma_modo=FirmaModo.SESION)

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        en_transito = ctx.cargador.ubicacion_virtual(UbicacionVirtual.EN_TRANSITO)
        # Cada movimiento conserva origen (En tránsito) y destino (el almacén que recibe, X-07).
        movimientos = []
        reglas_del_vale = [m.regla for m in evaluacion.motivos_vale if m.nivel != Nivel.VERDE]
        for r in evaluacion.renglones:
            assert r.articulo_id is not None
            reglas = list(REGLAS_DE_LA_RECEPCION)
            for regla in [*reglas_del_vale, *motivos_ids(r)]:
                if regla not in reglas:
                    reglas.append(regla)
            movimientos.append(
                MovimientoNuevo(
                    renglon=r.renglon,
                    articulo_id=r.articulo_id,
                    pieza_id=r.pieza_id,
                    cantidad=r.cantidad,
                    origen_id=en_transito.id,
                    destino_id=ctx.ubicacion_almacen.id,
                    condicion=None,
                    nivel=r.nivel,
                    reglas=reglas,
                    observacion=r.extra.get("observacion"),
                )
            )
        return movimientos

    def al_confirmar(
        self,
        ctx: ContextoVale,
        cuerpo: ValeIn,
        evaluacion: Evaluacion,
        vale: Vale,
        movimientos: list[Any],
    ) -> None:
        """X-13: el traspaso original queda Recibido (nada pendiente) o Recibido con diferencias
        (lo no recibido sigue En tránsito). Es la única excepción a "los vales no se actualizan"
        (invariante 5): cambia `vale.estado`, nunca sus renglones."""
        repo = TraspasoRepository(ctx.session)
        assert cuerpo.vale_origen_id is not None
        traspaso = repo.vale(cuerpo.vale_origen_id)
        assert traspaso is not None
        traspaso.estado = estado_despues_de_recibir(repo.pendiente_total(traspaso.id))
        ctx.session.flush()

    # ------------------------------------------------------------ por recibir (lista)

    def por_recibir(
        self,
        servicio: MovimientoService,
        usuario: Usuario,
        solo_contar: bool = False,
        almacen_id: uuid.UUID | None = None,
    ) -> PorRecibirOut | TotalPorRecibirOut:
        """`GET /api/traspasos/por-recibir`: los traspasos EN_TRANSITO (o con diferencias) hacia el
        almacén de la sesión, del más antiguo al más nuevo, con sus renglones y lo ya recibido.

        Sin `almacenes.todos` solo ve los de su almacén (un `almacen_id` ajeno es 409
        `ALMACEN_CAMBIO`). Con `almacenes.todos`, `almacen_id` filtra y sin él ve los de todos los
        almacenes. `solo_contar` devuelve solo `{total}`: es una consulta ligera para el
        contador del inicio."""
        if servicio.acceso.puede_operar_todos_los_almacenes(usuario):
            if almacen_id is not None:
                servicio.almacenes.obtener(almacen_id)
            destino_id = almacen_id
        else:
            destino_id = servicio.resolver_almacen_del_vale(usuario, almacen_id)

        repo = TraspasoRepository(servicio.session)
        if solo_contar:
            return TotalPorRecibirOut(total=repo.contar_por_recibir(destino_id))

        vales = repo.por_recibir(destino_id)
        lineas = repo.lineas_de([v.id for v in vales])
        recepciones = repo.recepciones_de([v.id for v in vales])
        almacenes = repo.almacenes(
            [v.almacen_id for v in vales] + [v.destino_almacen_id for v in vales]
        )
        usuarios = repo.usuarios(
            [v.responsable_id for v in vales]
            + [r.responsable_id for rs in recepciones.values() for r in rs]
        )

        def resumen(almacen_id: uuid.UUID) -> AlmacenResumenOut:
            a = almacenes[almacen_id]
            return AlmacenResumenOut(id=a.id, clave=a.clave, nombre=a.nombre)

        def persona(usuario_id: uuid.UUID) -> PersonaOut:
            return PersonaOut(id=usuario_id, nombre=usuarios[usuario_id].nombre)

        elementos = []
        for v in vales:
            renglones = [
                RenglonPorRecibirOut(
                    renglon=linea.renglon,
                    articulo_id=linea.articulo.id,
                    articulo=linea.articulo.nombre,
                    marca=linea.articulo.marca,
                    modelo=linea.articulo.modelo,
                    talla=linea.articulo.talla,
                    codigo=linea.pieza.codigo if linea.pieza else linea.articulo.codigo,
                    pieza_id=linea.pieza.id if linea.pieza else None,
                    numero_serie=linea.pieza.numero_serie if linea.pieza else None,
                    cantidad_enviada=linea.enviada,
                    cantidad_recibida=linea.recibida,
                    cantidad_pendiente=linea.pendiente,
                )
                for linea in lineas[v.id]
            ]
            elementos.append(
                TraspasoPorRecibirOut(
                    id=v.id,
                    folio=v.folio,
                    token=v.token,
                    estado=v.estado,
                    origen=resumen(v.almacen_id),
                    destino=resumen(v.destino_almacen_id),
                    envio=persona(v.responsable_id),
                    creado_en=v.creado_en,
                    pendiente_total=sum(r.cantidad_pendiente for r in renglones),
                    renglones=renglones,
                    recepciones=[
                        RecepcionResumenOut(
                            id=r.id,
                            folio=r.folio,
                            creado_en=r.creado_en,
                            recibio=persona(r.responsable_id),
                        )
                        for r in recepciones[v.id]
                    ],
                )
            )
        return PorRecibirOut(total=len(elementos), elementos=elementos)
