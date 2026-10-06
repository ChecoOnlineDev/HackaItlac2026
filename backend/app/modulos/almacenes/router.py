"""Endpoints del módulo `almacenes`: la red y las existencias (`inventario.ver`)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.paginacion import PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import UsuarioActual, requiere_permiso
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.dependencies import AlmacenServiceDep
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado
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
    usuario: UsuarioActual,
    session: SesionDep,
    service: AlmacenServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[AlmacenFilters, Query()],
) -> ExistenciasOut:
    """`inventario.ver`. Existencias y disponibles por artículo (sin costos). AC-06: sin
    `almacenes.todos`, solo las del almacén asignado; otro almacén responde 404, igual que uno
    que no existe."""
    if not AccesoService(session).en_alcance(usuario, almacen_id):
        raise AlmacenNoEncontrado()
    return service.existencias(almacen_id, filtros, pagina)
