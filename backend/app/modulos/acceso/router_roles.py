"""Roles y permisos (FEAT-006, AC-08 a AC-11). Todo pide `acceso.roles`.

Las reglas viven en `service_roles.py`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.schemas import (
    PermisoOut,
    RolCreate,
    RolDetalleOut,
    RolPermisosIn,
    RolUpdate,
)
from app.modulos.acceso.service_roles import RolAdminService, catalogo_de_permisos

router = APIRouter(tags=["roles"])


def get_service(session: SesionDep) -> RolAdminService:
    return RolAdminService(session)


ServiceDep = Annotated[RolAdminService, Depends(get_service)]
QuienAdministra = Annotated[Usuario, Depends(requiere_permiso(P.ACCESO_ROLES))]


@router.get("/permisos", response_model=list[PermisoOut])
def listar_permisos(_: QuienAdministra) -> list[PermisoOut]:
    """`acceso.roles`. El catálogo fijo de permisos, con su módulo y sus requisitos."""
    return catalogo_de_permisos()


@router.get("/roles", response_model=list[RolDetalleOut])
def listar_roles(_: QuienAdministra, service: ServiceDep) -> list[RolDetalleOut]:
    """`acceso.roles`. Roles con su número de usuarios y sus permisos."""
    return service.listar()


@router.post("/roles", response_model=RolDetalleOut, status_code=status.HTTP_201_CREATED)
def crear_rol(datos: RolCreate, actor: QuienAdministra, service: ServiceDep) -> RolDetalleOut:
    """`acceso.roles`. Rol nuevo con nombre único y los permisos que se elijan (AC-08)."""
    return service.crear(actor, datos)


@router.get("/roles/{rol_id}", response_model=RolDetalleOut)
def ver_rol(rol_id: uuid.UUID, _: QuienAdministra, service: ServiceDep) -> RolDetalleOut:
    """`acceso.roles`. Un rol con la lista de sus permisos."""
    return service.ver(rol_id)


@router.patch("/roles/{rol_id}", response_model=RolDetalleOut)
def editar_rol(
    rol_id: uuid.UUID, datos: RolUpdate, actor: QuienAdministra, service: ServiceDep
) -> RolDetalleOut:
    """`acceso.roles`. Nombre, descripción y activo (AC-09, AC-11)."""
    return service.editar(actor, rol_id, datos)


@router.put("/roles/{rol_id}/permisos", response_model=RolDetalleOut)
def reemplazar_permisos(
    rol_id: uuid.UUID, datos: RolPermisosIn, actor: QuienAdministra, service: ServiceDep
) -> RolDetalleOut:
    """`acceso.roles`. Deja al rol exactamente con esos permisos (AC-08, AC-09, AC-10)."""
    return service.reemplazar_permisos(actor, rol_id, datos.permisos)


@router.delete("/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_rol(rol_id: uuid.UUID, actor: QuienAdministra, service: ServiceDep) -> Response:
    """`acceso.roles`. Solo un rol sin usuarios que no sea de los iniciales (AC-11)."""
    service.eliminar(actor, rol_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
