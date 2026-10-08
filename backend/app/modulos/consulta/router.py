"""Endpoints del módulo `consulta`: escaneo, búsqueda, ficha de pieza y reportes. SOLO LEE.

Ningún endpoint de este módulo escribe en la base: un `GET` nunca hace `commit`. Cada reporte
acepta `formato=csv` y entonces responde el archivo completo con los mismos filtros.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.paginacion import PaginacionDep
from app.modulos.acceso.dependencies import UsuarioActual, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.dependencies import (
    ConsultaServiceDep,
    SeguimientoServiceDep,
    requiere_alguno,
)
from app.modulos.consulta.exportacion import respuesta_csv
from app.modulos.consulta.router_tablero import router as router_tablero
from app.modulos.consulta.schemas import (
    AdeudoReporteItem,
    AdeudosFilters,
    BusquedaOut,
    ConsumoFilters,
    ConsumoReporteItem,
    EscaneoOut,
    ExistenciaReporteItem,
    ExistenciasFilters,
    FormatoReporte,
    MovimientoReporteItem,
    MovimientosFilters,
    PaginaReporte,
    PiezaFichaOut,
    UsuariosOpcionesOut,
)
from app.modulos.consulta.schemas_seguimiento import (
    CantidadFilters,
    PaginaCantidad,
    PaginaSeguimiento,
    SeguimientoFilters,
)

router = APIRouter(tags=["consulta"])
router.include_router(router_tablero)

VerPieza = Annotated[Usuario, Depends(requiere_permiso(P.CATALOGO_VER))]
VerExistencias = Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_EXISTENCIAS))]
VerQuienTieneQue = Annotated[
    Usuario, Depends(requiere_alguno(P.REPORTES_EXISTENCIAS, P.RESGUARDO_VER))
]
VerBitacora = Annotated[Usuario, Depends(requiere_alguno(P.BITACORA_VER, P.REPORTES_MOVIMIENTOS))]
VerAdeudos = Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_ADEUDOS))]
VerConsumo = Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_CONSUMO))]


@router.get("/escaneo/{codigo}", response_model=EscaneoOut)
def escanear(
    codigo: str,
    usuario: UsuarioActual,
    service: ConsultaServiceDep,
    almacen_id: Annotated[uuid.UUID | None, Query()] = None,
) -> EscaneoOut:
    """Sesión. Identifica un código: `{tipo, id, resumen}`. Lo que el usuario no puede ver llega
    como DESCONOCIDO (C-01 a C-04). Con `almacen_id` (origen de un traspaso, TR-11) el artículo y
    la pieza traen `disponible`: lo que hay en ese almacén."""
    return service.escanear(codigo, usuario, almacen_id)


@router.get("/busqueda", response_model=BusquedaOut)
def buscar(
    usuario: UsuarioActual,
    service: ConsultaServiceDep,
    pagina: PaginacionDep,
    q: Annotated[str, Query(max_length=100)] = "",
    almacen_id: Annotated[uuid.UUID | None, Query()] = None,
) -> BusquedaOut:
    """Sesión. Artículos, piezas y trabajadores que coinciden con `q` (C-06). Menos de dos
    caracteres no busca. Cada grupo es una lista paginada `{elementos, total}`. Con `almacen_id`
    (origen de un traspaso, TR-11) solo ofrece artículos y piezas que hay en ese almacén, con su
    `disponible`."""
    return service.buscar(q, usuario, pagina, almacen_id)


@router.get("/piezas/{pieza_id}", response_model=PiezaFichaOut)
def ficha_pieza(
    pieza_id: uuid.UUID, usuario: VerPieza, service: ConsultaServiceDep
) -> PiezaFichaOut:
    """`catalogo.ver`. Estado, inspección, ubicación e historial de la pieza (C-02). Sin
    `almacenes.todos`, una pieza fuera del alcance del usuario responde 404 (AC-06)."""
    return service.ficha_pieza(pieza_id, usuario)


@router.get("/seguimiento/piezas", response_model=PaginaSeguimiento)
def seguimiento_piezas(
    usuario: VerQuienTieneQue,
    service: SeguimientoServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[SeguimientoFilters, Query()],
):
    """`reportes.existencias` o `resguardo.ver` (SG-04). Seguimiento de piezas (C-13): dónde está
    cada pieza o quién la tiene, desde cuándo y con qué vale, con un resumen de conteos. Solo lo
    que el usuario puede ver (AC-06). Con `formato=csv` descarga el archivo."""
    if filtros.formato == FormatoReporte.CSV:
        return respuesta_csv(*service.csv_seguimiento_piezas(filtros, usuario))
    return service.seguimiento_piezas(filtros, usuario, pagina)


@router.get("/seguimiento/cantidad", response_model=PaginaCantidad)
def seguimiento_cantidad(
    usuario: VerQuienTieneQue,
    service: SeguimientoServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[CantidadFilters, Query()],
):
    """`reportes.existencias` o `resguardo.ver` (SG-01, SG-04). Los artículos por cantidad que
    están en resguardo de un trabajador: cuánto, desde cuándo y con qué vale. Sin
    `almacenes.todos`, solo lo entregado desde su almacén (AC-06). Con `formato=csv` descarga el
    archivo."""
    if filtros.formato == FormatoReporte.CSV:
        return respuesta_csv(*service.csv_seguimiento_cantidad(filtros, usuario))
    return service.seguimiento_cantidad(filtros, usuario, pagina)


@router.get("/reportes/existencias", response_model=PaginaReporte[ExistenciaReporteItem])
def reporte_existencias(
    usuario: VerExistencias,
    service: ConsultaServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[ExistenciasFilters, Query()],
):
    """`reportes.existencias`. Por almacén y artículo. Con `formato=csv` descarga el archivo."""
    if filtros.formato == FormatoReporte.CSV:
        return respuesta_csv(*service.csv_existencias(filtros, usuario))
    return service.reporte_existencias(filtros, usuario, pagina)


@router.get("/reportes/usuarios", response_model=UsuariosOpcionesOut)
def opciones_usuarios(usuario: VerBitacora, service: ConsultaServiceDep) -> UsuariosOpcionesOut:
    """`bitacora.ver` o `reportes.movimientos` (cualquiera de los dos). Quién ha hecho vales,
    para el filtro «quién lo hizo» (C-11)."""
    return service.opciones_usuarios(usuario)


@router.get("/reportes/movimientos", response_model=PaginaReporte[MovimientoReporteItem])
def reporte_movimientos(
    usuario: VerBitacora,
    service: ConsultaServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[MovimientosFilters, Query()],
):
    """`bitacora.ver` o `reportes.movimientos` (cualquiera de los dos). La bitácora
    del almacén: lo que sale, lo que llega y las entradas (SG-05). Sin `almacenes.todos`, solo el
    almacén asignado."""
    if filtros.formato == FormatoReporte.CSV:
        return respuesta_csv(*service.csv_movimientos(filtros, usuario))
    return service.reporte_movimientos(filtros, usuario, pagina)


@router.get("/reportes/adeudos", response_model=PaginaReporte[AdeudoReporteItem])
def reporte_adeudos(
    usuario: VerAdeudos,
    service: ConsultaServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[AdeudosFilters, Query()],
):
    """`reportes.adeudos`. Lo pendiente por trabajador; `solo_no_vigentes` filtra a quienes ya no
    son vigentes."""
    if filtros.formato == FormatoReporte.CSV:
        return respuesta_csv(*service.csv_adeudos(filtros, usuario))
    return service.reporte_adeudos(filtros, usuario, pagina)


@router.get("/reportes/consumo", response_model=PaginaReporte[ConsumoReporteItem])
def reporte_consumo(
    usuario: VerConsumo,
    service: ConsultaServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[ConsumoFilters, Query()],
):
    """`reportes.consumo`. Consumo neto de consumibles por artículo y trabajador (C-08)."""
    if filtros.formato == FormatoReporte.CSV:
        return respuesta_csv(*service.csv_consumo(filtros, usuario))
    return service.reporte_consumo(filtros, usuario, pagina)
