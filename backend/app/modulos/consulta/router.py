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
from app.modulos.consulta.dependencies import ConsultaServiceDep
from app.modulos.consulta.exportacion import respuesta_csv
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

router = APIRouter(tags=["consulta"])

VerPieza = Annotated[Usuario, Depends(requiere_permiso(P.CATALOGO_VER))]
VerExistencias = Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_EXISTENCIAS))]
VerMovimientos = Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_MOVIMIENTOS))]
VerAdeudos = Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_ADEUDOS))]
VerConsumo = Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_CONSUMO))]


@router.get("/escaneo/{codigo}", response_model=EscaneoOut)
def escanear(codigo: str, usuario: UsuarioActual, service: ConsultaServiceDep) -> EscaneoOut:
    """Sesión. Identifica un código: `{tipo, id, resumen}`. Lo que el usuario no puede ver llega
    como DESCONOCIDO (C-01 a C-04)."""
    return service.escanear(codigo, usuario)


@router.get("/busqueda", response_model=BusquedaOut)
def buscar(
    usuario: UsuarioActual,
    service: ConsultaServiceDep,
    pagina: PaginacionDep,
    q: Annotated[str, Query(max_length=100)] = "",
) -> BusquedaOut:
    """Sesión. Artículos, piezas y trabajadores que coinciden con `q` (C-06). Menos de dos
    caracteres no busca. Cada grupo es una lista paginada `{elementos, total}`."""
    return service.buscar(q, usuario, pagina)


@router.get("/piezas/{pieza_id}", response_model=PiezaFichaOut)
def ficha_pieza(pieza_id: uuid.UUID, _: VerPieza, service: ConsultaServiceDep) -> PiezaFichaOut:
    """`catalogo.ver`. Estado, inspección, ubicación e historial de la pieza (C-02)."""
    return service.ficha_pieza(pieza_id)


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
def opciones_usuarios(usuario: VerMovimientos, service: ConsultaServiceDep) -> UsuariosOpcionesOut:
    """`reportes.movimientos`. Quién ha hecho vales, para el filtro «quién lo hizo» (C-11)."""
    return service.opciones_usuarios(usuario)


@router.get("/reportes/movimientos", response_model=PaginaReporte[MovimientoReporteItem])
def reporte_movimientos(
    usuario: VerMovimientos,
    service: ConsultaServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[MovimientosFilters, Query()],
):
    """`reportes.movimientos`. Bitácora; sin `almacenes.todos`, solo el almacén asignado."""
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
