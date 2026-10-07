"""Endpoints del tablero (`/api/tablero`): tarjetas y lo más usado. SOLO LEEN.

Los dos piden `tablero.ver`; el alcance por almacén (TB-01, AC-06) lo decide el servicio.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.dependencies import TableroServiceDep
from app.modulos.consulta.schemas_tablero import (
    ConsumoTableroFilters,
    ConsumoTableroOut,
    ResumenTableroOut,
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
