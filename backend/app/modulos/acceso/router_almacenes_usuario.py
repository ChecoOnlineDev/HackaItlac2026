"""Cambio de almacén activo y asignación de conjuntos (AC-39, AC-41)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.db import SesionDep
from app.modulos.acceso.dependencies import UsuarioActual
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.schemas import AlmacenActivoIn, AsignarAlmacenesIn, PersonalOut, SesionOut
from app.modulos.acceso.service_almacenes_usuario import AlmacenesUsuarioService
from app.modulos.consulta.dependencies import requiere_alguno

router = APIRouter(tags=["acceso"])


def get_service(session: SesionDep):
    return AlmacenesUsuarioService(session)


ServiceDep = Annotated[AlmacenesUsuarioService, Depends(get_service)]
Asignador = Annotated[
    Usuario, Depends(requiere_alguno("acceso.usuarios", "almacenes.asignar_personal"))
]


@router.put("/sesion/almacen", response_model=SesionOut)
def cambiar_activo(datos: AlmacenActivoIn, usuario: UsuarioActual, service: ServiceDep):
    return service.cambiar_activo(usuario, datos)


@router.put("/usuarios/{id}/almacenes", response_model=PersonalOut)
def asignar_conjunto(
    id: uuid.UUID, datos: AsignarAlmacenesIn, usuario: Asignador, service: ServiceDep
):
    return service.asignar_conjunto(id, datos, usuario)
