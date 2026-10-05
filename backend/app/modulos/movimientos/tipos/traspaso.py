"""Tipo TRASPASO, la salida (US-TRS-001, fase 5): almacén de origen -> EN_TRANSITO.

El traspaso tiene dos pasos (X-01): la salida (este tipo) y la recepción (`recepcion.py`). Entre
ambos la existencia está En tránsito y no cuenta para ningún almacén. El vale queda en estado
`EN_TRANSITO`, con `destino_almacen_id`, folio `CLAVE-TRS-000001` y QR (X-06). Quien envía firma
con su sesión (F-09).

Reglas: X-01 a X-04, X-06, X-07, X-09, F-09 (en `evaluador_traspasos.py` las que se evalúan).
Fuera de alcance: X-05 (aviso por mínimo, FEAT-004), X-14 (cancelar lo hace CANCELACION).

Cuerpo: `destino_almacen_id` y los renglones (código de la pieza, o del artículo y cantidad). No
lleva trabajador, ni credencial, ni condición, ni costos.

Mismo criterio que E-15 y E-16 de la entrega: una pieza repetida en el borrador se ignora y un
artículo por cantidad repetido suma.
"""

import uuid

from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen, EstadoAlmacen, UbicacionVirtual
from app.modulos.movimientos.cargador import hechos_de_articulo, hechos_de_pieza
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import Motivo
from app.modulos.movimientos.evaluador_traspasos import (
    HechosAlmacen,
    HechosRenglonTraspaso,
    evaluar_renglon_traspaso,
    regla_x03_ruta,
)
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
    )


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

    # ------------------------------------------------------------------ evaluación

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        carga = ctx.cargador
        repo = TraspasoRepository(ctx.session)
        assert cuerpo.destino_almacen_id is not None
        evaluacion = Evaluacion()

        destino = repo.almacen(cuerpo.destino_almacen_id)
        if destino is None:
            ruta = Motivo("X-03", Nivel.ROJO, "El almacén de destino no existe.")
        else:
            ruta = regla_x03_ruta(hechos_de_almacen(ctx.almacen), hechos_de_almacen(destino))
        evaluacion.motivos_vale = [ruta]

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
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=numero,
                    codigo=renglon.codigo,
                    cantidad=renglon.cantidad,
                    motivos=evaluar_renglon_traspaso(hechos),
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

    # ---------------------------------------------------------------- confirmación

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
