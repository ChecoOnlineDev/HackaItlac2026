"""Endpoints del tablero (`/api/tablero`): tarjetas y lo más usado. SOLO LEEN.

Resumen y consumo piden `tablero.ver`; `/valor` pide `reportes.valor_inventario`. El alcance
por almacén (TB-01, AC-06) lo decide el servicio.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.dependencies import TableroServiceDep, ValorServiceDep
from app.modulos.consulta.schemas_tablero import (
    ConsumoTableroFilters,
    ConsumoTableroOut,
    ResumenTableroOut,
    ValorInventarioOut,
)

router = APIRouter(prefix="/tablero", tags=["tablero"])

VerTablero = Annotated[Usuario, Depends(requiere_permiso(P.TABLERO_VER))]


@router.get("/resumen", response_model=ResumenTableroOut)
def resumen(
    usuario: VerTablero,
    service: TableroServiceDep,
    almacen_id: uuid.UUID | None = None,
) -> ResumenTableroOut:
    """`tablero.ver`. Las tarjetas del Inicio. Sin `almacenes.todos`, `almacen_id` se ignora y
    se usa el almacén de la sesión (TB-01)."""
    return service.resumen(usuario, almacen_id)


@router.get("/consumo", response_model=ConsumoTableroOut)
def consumo(
    usuario: VerTablero,
    service: TableroServiceDep,
    filtros: Annotated[ConsumoTableroFilters, Query()],
) -> ConsumoTableroOut:
    """`tablero.ver`. Lo más usado en el rango, neto de cancelaciones y por categoría (TB-02)."""
    return service.consumo(usuario, filtros)


@router.get("/valor", response_model=ValorInventarioOut)
def valor(
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_VALOR_INVENTARIO))],
    service: ValorServiceDep,
    almacen_id: uuid.UUID | None = None,
) -> ValorInventarioOut:
    """`reportes.valor_inventario`. Solo totales en pesos (FEAT-012); nunca el costo de un
    artículo. El alcance es el de AC-06: sin `almacenes.todos`, `almacen_id` se ignora."""
    return service.valor(usuario, almacen_id)
