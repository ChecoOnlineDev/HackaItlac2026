"""Usuarios y personal por almacén (FEAT-006); los roles están en `router_roles.py`.

`/personal` y `PATCH /usuarios/{id}/almacen` piden `almacenes.asignar_personal` (el Supervisor
puede, sin acceso a roles ni altas). El resto pide `acceso.usuarios`. Las reglas viven en
`service_usuarios.py`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.paginacion import Pagina, PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import FiltrosUsuarios
from app.modulos.acceso.schemas import (
    AsignarAlmacenIn,
    PersonalOut,
    RestablecerContrasenaIn,
    UsuarioCreate,
    UsuarioOut,
    UsuarioUpdate,
)
from app.modulos.acceso.service_usuarios import UsuarioAdminService

router = APIRouter(tags=["usuarios"])


def get_service(session: SesionDep) -> UsuarioAdminService:
    return UsuarioAdminService(session)


ServiceDep = Annotated[UsuarioAdminService, Depends(get_service)]

QuienAdministra = Annotated[Usuario, Depends(requiere_permiso(P.ACCESO_USUARIOS))]
QuienAsignaPersonal = Annotated[Usuario, Depends(requiere_permiso(P.ALMACENES_ASIGNAR_PERSONAL))]


@router.get("/personal", response_model=Pagina[PersonalOut])
def listar_personal(
    actor: QuienAsignaPersonal,
    service: ServiceDep,
    pagina: PaginacionDep,
    almacen_id: uuid.UUID | None = None,
    sin_almacen: bool = False,
    q: str | None = None,
) -> Pagina[PersonalOut]:
    """`almacenes.asignar_personal`. Quienes operan un almacén; filtros por almacén, sin almacén y
    texto. Sin `almacenes.todos`, solo el personal de su almacén y quienes no tienen uno."""
    elementos, total = service.listar_personal(
        actor,
        almacen_id=almacen_id,
        sin_almacen=sin_almacen,
        q=q,
        limit=pagina.limit,
        offset=pagina.offset,
    )
    return Pagina(elementos=elementos, total=total)


@router.patch("/usuarios/{usuario_id}/almacen", response_model=PersonalOut)
def asignar_almacen(
    usuario_id: uuid.UUID, datos: AsignarAlmacenIn, actor: QuienAsignaPersonal, service: ServiceDep
) -> PersonalOut:
    """`almacenes.asignar_personal`. Asigna, mueve o deja sin almacén (AC-12, AC-13)."""
    return service.mover_almacen(actor, usuario_id, datos.almacen_id)


@router.get("/usuarios", response_model=Pagina[UsuarioOut])
def listar_usuarios(
    _: QuienAdministra,
    service: ServiceDep,
    pagina: PaginacionDep,
    q: str | None = None,
    rol_id: uuid.UUID | None = None,
    almacen_id: uuid.UUID | None = None,
    sin_almacen: bool = False,
    activo: bool | None = None,
) -> Pagina[UsuarioOut]:
    """`acceso.usuarios`. Lista de usuarios con filtros."""
    elementos, total = service.listar_usuarios(
        FiltrosUsuarios(
            q=q, rol_id=rol_id, almacen_id=almacen_id, sin_almacen=sin_almacen, activo=activo
        ),
        limit=pagina.limit,
        offset=pagina.offset,
    )
    return Pagina(elementos=elementos, total=total)


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: UsuarioCreate, actor: QuienAdministra, service: ServiceDep) -> UsuarioOut:
    """`acceso.usuarios`. Alta con contraseña inicial, rol y almacén."""
    return service.crear(actor, datos)


@router.get("/usuarios/{usuario_id}", response_model=UsuarioOut)
def ver_usuario(usuario_id: uuid.UUID, _: QuienAdministra, service: ServiceDep) -> UsuarioOut:
    """`acceso.usuarios`. Un usuario."""
    return service.ver(usuario_id)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
def editar_usuario(
    usuario_id: uuid.UUID, datos: UsuarioUpdate, actor: QuienAdministra, service: ServiceDep
) -> UsuarioOut:
    """`acceso.usuarios`. Nombre, rol, activo y almacén (AC-09)."""
    return service.editar(actor, usuario_id, datos)


@router.post("/usuarios/{usuario_id}/contrasena", response_model=UsuarioOut)
def restablecer_contrasena(
    usuario_id: uuid.UUID,
    datos: RestablecerContrasenaIn,
    actor: QuienAdministra,
    service: ServiceDep,
) -> UsuarioOut:
    """`acceso.usuarios`. Restablece la contraseña (y el PIN si se manda) y los bloqueos."""
    return service.restablecer_contrasena(actor, usuario_id, datos.contrasena, datos.pin)
