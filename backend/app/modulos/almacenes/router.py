"""Endpoints del módulo `almacenes`: la red y las existencias (`inventario.ver`)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.paginacion import PaginacionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.dependencies import AlmacenServiceDep
from app.modulos.almacenes.schemas import AlmacenFilters, AlmacenOut, ExistenciasOut

router = APIRouter(prefix="/almacenes", tags=["almacenes"])


@router.get(
    "", response_model=list[AlmacenOut], dependencies=[Depends(requiere_permiso(P.INVENTARIO_VER))]
)
def listar_almacenes(service: AlmacenServiceDep) -> list[AlmacenOut]:
    """`inventario.ver`. Los almacenes con su red: quién los surte y a quién surten."""
    return service.listar()


@router.get(
    "/{almacen_id}/existencias",
    response_model=ExistenciasOut,
    dependencies=[Depends(requiere_permiso(P.INVENTARIO_VER))],
)
def existencias_del_almacen(
    almacen_id: uuid.UUID,
    service: AlmacenServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[AlmacenFilters, Query()],
) -> ExistenciasOut:
    """`inventario.ver`. Existencias y disponibles por artículo (sin costos)."""
    return service.existencias(almacen_id, filtros, pagina)
