"""Tipo ENTRADA (US-INV-001): PROVEEDOR -> almacén.

Reglas: I-01 a I-04, I-07, I-09, RG-01, RG-05, RG-06, RG-09, RG-12. Por cantidad aumenta la
existencia; por pieza cada renglón trae su pieza (código, serie e inspección inicial opcional) y
la entrada la crea con `CatalogoService.registrar_pieza` (su código queda registrado, I-02).

La inspección inicial (I-03) se registra con `InspeccionService.registrar_inicial` del módulo
`inspecciones`. Sin ella la pieza queda pendiente (sin inspección vigente) y no se puede
entregar (E-06). El costo unitario no va en el vale: se captura en `catalogo` con
`catalogo.costos` (I-04, RG-12).
"""

import uuid
from typing import TYPE_CHECKING, Any

from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.cargador import hechos_de_articulo
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import (
    HechosInspeccionInicial,
    HechosRenglonEntrada,
    evaluar_renglon_entrada,
)
from app.modulos.movimientos.models import FirmaModo, TipoVale, Vale
from app.modulos.movimientos.schemas import RenglonIn, ValeIn
from app.modulos.movimientos.tipos.base import ManejadorTipo, motivos_ids, vista_articulo

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.modulos.movimientos.service import MovimientoService

# Clave del almacén al que entran las compras si quien captura puede elegir y no indica uno (I-01).
ALMACEN_COMPRAS = "KEP"


def servicio_inspecciones(session: Session) -> Any:
    """`InspeccionService` del módulo `inspecciones`. Punto de enchufe: las pruebas lo
    reemplazan por un doble. Firma acordada:

        registrar_inicial(pieza_id, *, fecha, resultado, observacion, usuario_id) -> Inspeccion

    (solo `flush`; fija el estado y `inspeccion_vigente_hasta` con
    `CatalogoService.actualizar_estado_pieza`)."""
    from app.modulos.inspecciones.service import InspeccionService

    return InspeccionService(session)


def _campo(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


class EntradaTipo(ManejadorTipo):
    tipo = TipoVale.ENTRADA
    permiso = P.INVENTARIO_ENTRADAS
    requiere_firma = False
    firma_modo = FirmaModo.SESION  # F-03: basta la sesión de Compras

    # ------------------------------------------------------------------ validación

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        if cuerpo.trabajador_id is not None:
            raise _campo("trabajador_id", "Una entrada no lleva trabajador.")
        if confirmar and not cuerpo.renglones:
            raise _campo("renglones", "Agrega al menos un renglón.")

    def almacen_operativo(
        self, servicio: MovimientoService, usuario: Any, cuerpo: ValeIn
    ) -> uuid.UUID:
        """El almacén que recibe: `almacen_id` o `destino_almacen_id`; quien puede elegir y no
        indica uno entra por Kepler (I-01)."""
        indicado = cuerpo.almacen_id or cuerpo.destino_almacen_id
        return servicio.resolver_almacen_del_vale(usuario, indicado, por_defecto=ALMACEN_COMPRAS)

    def normalizar_renglones(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[RenglonIn]:
        """Un artículo por cantidad repetido suma (como E-16). Las piezas no se juntan: cada una
        es un renglón con su código y su serie."""
        salida: list[RenglonIn] = []
        por_articulo: dict[uuid.UUID, int] = {}
        for renglon in cuerpo.renglones:
            ident = ctx.cargador.identificar(renglon.codigo)
            if (
                ident.tipo == "ARTICULO"
                and ident.articulo
                and ident.articulo.control == "CANTIDAD"
                and renglon.pieza is None
            ):
                indice = por_articulo.get(ident.articulo.id)
                if indice is not None:
                    previo = salida[indice]
                    salida[indice] = previo.model_copy(
                        update={"cantidad": previo.cantidad + renglon.cantidad}
                    )
                    continue
                por_articulo[ident.articulo.id] = len(salida)
            salida.append(renglon)
        return salida

    # ------------------------------------------------------------------ evaluación

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        carga = ctx.cargador
        evaluacion = Evaluacion()
        codigos_vistos: set[str] = set()
        series_vistas: set[tuple[uuid.UUID, str]] = set()
        for numero, renglon in enumerate(cuerpo.renglones, start=1):
            ident = carga.identificar(renglon.codigo)
            articulo = ident.articulo if ident.tipo == "ARTICULO" else None
            datos_pieza = renglon.pieza
            codigo_pieza = datos_pieza.codigo.strip() if datos_pieza else None
            serie = datos_pieza.numero_serie if datos_pieza else None
            repetida = False
            serie_en_uso = False
            codigo_en_uso = None
            inspeccion = None
            if articulo is not None and articulo.control == "PIEZA" and datos_pieza is not None:
                clave_codigo = (codigo_pieza or "").casefold()
                clave_serie = (articulo.id, (serie or "").casefold())
                repetida = clave_codigo in codigos_vistos or (
                    bool(serie) and clave_serie in series_vistas
                )
                codigos_vistos.add(clave_codigo)
                if serie:
                    series_vistas.add(clave_serie)
                if codigo_pieza:
                    codigo_en_uso = carga.descripcion_de_codigo(codigo_pieza)
                if serie:
                    serie_en_uso = carga.repository.pieza_por_serie(articulo.id, serie) is not None
                if datos_pieza.inspeccion is not None:
                    inspeccion = HechosInspeccionInicial(
                        fecha=datos_pieza.inspeccion.fecha or ctx.hoy,
                        resultado=str(datos_pieza.inspeccion.resultado),
                        observacion=datos_pieza.inspeccion.observacion,
                    )
            hechos = HechosRenglonEntrada(
                codigo=renglon.codigo,
                cantidad=renglon.cantidad,
                articulo=hechos_de_articulo(articulo) if articulo is not None else None,
                pieza_codigo=codigo_pieza,
                pieza_serie=serie,
                tiene_datos_pieza=datos_pieza is not None,
                codigo_pieza_en_uso=codigo_en_uso,
                serie_en_uso=serie_en_uso,
                repetida_en_vale=repetida,
                inspeccion=inspeccion,
                codigo_no_es_articulo=ident.tipo in ("PIEZA", "OTRO"),
            )
            resultado = evaluar_renglon_entrada(hechos, ctx.hoy)
            pieza_vista = None
            if articulo is not None and articulo.control == "PIEZA" and datos_pieza is not None:
                pieza_vista = {
                    "id": None,
                    "codigo": codigo_pieza or "",
                    "numero_serie": serie,
                    "estado": (
                        "NO_APTO" if inspeccion and inspeccion.resultado == "NO_APTO" else "APTO"
                    ),
                    "inspeccion_vigente_hasta": None,
                    "pendiente_inspeccion": bool(articulo.requiere_inspeccion and not inspeccion),
                }
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=numero,
                    codigo=renglon.codigo,
                    cantidad=renglon.cantidad,
                    motivos=resultado.motivos,
                    articulo_id=articulo.id if articulo else None,
                    articulo=vista_articulo(hechos.articulo) if hechos.articulo else None,
                    pieza=pieza_vista,
                    disponible=None,
                    pide_observacion=resultado.pide_observacion,
                    requiere_confirmacion=resultado.requiere_confirmacion,
                    extra={
                        "control": articulo.control if articulo else None,
                        "pieza": datos_pieza,
                        "inspeccion": inspeccion,
                        "requiere_inspeccion": bool(articulo and articulo.requiere_inspeccion),
                        "observacion": renglon.observacion,
                    },
                )
            )
        return evaluacion

    # ---------------------------------------------------------------- confirmación

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        plan = PlanBloqueo()
        for renglon in cuerpo.renglones:
            ident = ctx.cargador.identificar(renglon.codigo)
            if ident.tipo == "ARTICULO" and ident.articulo is not None:
                plan.existencias.add((ctx.ubicacion_almacen.id, ident.articulo.id))
        return plan

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        return DatosVale(firma_modo=FirmaModo.SESION)

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        proveedor = ctx.cargador.ubicacion_virtual(UbicacionVirtual.PROVEEDOR)
        movimientos = []
        for r in evaluacion.renglones:
            assert r.articulo_id is not None
            if r.extra["control"] == "PIEZA":
                datos = r.extra["pieza"]
                pieza = ctx.cargador.catalogo.registrar_pieza(
                    r.articulo_id, datos.codigo, datos.numero_serie
                )
                r.pieza_id = pieza.id
            movimientos.append(
                MovimientoNuevo(
                    renglon=r.renglon,
                    articulo_id=r.articulo_id,
                    pieza_id=r.pieza_id,
                    cantidad=r.cantidad,
                    origen_id=proveedor.id,
                    destino_id=ctx.ubicacion_almacen.id,
                    nivel=r.nivel,
                    reglas=motivos_ids(r),
                    observacion=r.extra["observacion"],
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
        """I-03: registra la inspección inicial de cada pieza que la trae."""
        servicio = None
        for r in evaluacion.renglones:
            inspeccion = r.extra.get("inspeccion")
            if r.pieza_id is None or inspeccion is None or not r.extra["requiere_inspeccion"]:
                continue
            if servicio is None:
                servicio = servicio_inspecciones(ctx.session)
            servicio.registrar_inicial(
                r.pieza_id,
                fecha=inspeccion.fecha,
                resultado=r.extra["pieza"].inspeccion.resultado,
                observacion=inspeccion.observacion,
                usuario_id=ctx.usuario.id,
            )
