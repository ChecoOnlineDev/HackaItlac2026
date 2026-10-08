"""Dependencias de FastAPI del módulo `consulta`."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from app.core.excepciones import SinPermiso
from app.db import SesionDep
from app.modulos.acceso.dependencies import AccesoServiceDep, UsuarioActual
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import es_clave_valida
from app.modulos.consulta.service import ConsultaService
from app.modulos.consulta.service_seguimiento import SeguimientoService
from app.modulos.consulta.service_tablero import TableroService


def requiere_alguno(*claves: str) -> Callable[..., Usuario]:
    """Dependencia que exige AL MENOS UNO de los permisos `claves` (403 `SIN_PERMISO`) y
    devuelve el usuario. Se declara en el router, igual que `requiere_permiso`."""
    for clave in claves:
        if not es_clave_valida(clave):
            raise ValueError(f"Permiso desconocido: {clave!r}. Agrégalo a acceso/permisos.py")

    def dependencia(usuario: UsuarioActual, acceso: AccesoServiceDep) -> Usuario:
        if not any(acceso.tiene_permiso(usuario, c) for c in claves):
            raise SinPermiso()
        return usuario

    dependencia.__name__ = "requiere_alguno_" + "_".join(c.replace(".", "_") for c in claves)
    return dependencia


def get_consulta_service(session: SesionDep) -> ConsultaService:
    return ConsultaService(session)


ConsultaServiceDep = Annotated[ConsultaService, Depends(get_consulta_service)]


def get_seguimiento_service(session: SesionDep) -> SeguimientoService:
    return SeguimientoService(session)


SeguimientoServiceDep = Annotated[SeguimientoService, Depends(get_seguimiento_service)]


def get_tablero_service(session: SesionDep) -> TableroService:
    return TableroService(session)


TableroServiceDep = Annotated[TableroService, Depends(get_tablero_service)]
