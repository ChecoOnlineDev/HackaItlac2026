"""Dependencias reutilizables de FastAPI para autenticación y permisos.

Uso en cualquier `router.py`:

    from app.modulos.acceso.dependencies import UsuarioActual, requiere_permiso
    from app.modulos.acceso.permisos import P

    @router.post("/vales")
    def crear(usuario: Annotated[Usuario, Depends(requiere_permiso(P.ENTREGAS_CREAR))], ...):
        ...

El rol, los permisos y el almacén se leen de la base en CADA petición; nada se guarda entre
peticiones, así un cambio de permisos aplica en la siguiente (AC-10). Nunca se compara el nombre
del rol.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request

from app.config import get_settings
from app.core.excepciones import NoAutenticado, SinPermiso
from app.db import SesionDep
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import es_clave_valida
from app.modulos.acceso.service import AccesoService


def get_acceso_service(session: SesionDep) -> AccesoService:
    return AccesoService(session)


AccesoServiceDep = Annotated[AccesoService, Depends(get_acceso_service)]


def usuario_actual(request: Request, service: AccesoServiceDep) -> Usuario:
    """El usuario de la sesión. 401 `NO_AUTENTICADO` si no hay sesión, venció o está inactivo."""
    token = request.cookies.get(get_settings().cookie_nombre)
    usuario = service.usuario_de_token(token)
    if usuario is None:
        raise NoAutenticado()
    return usuario


UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]


def requiere_permiso(clave: str) -> Callable[..., Usuario]:
    """Dependencia que exige el permiso `clave` (403 `SIN_PERMISO`) y devuelve el usuario.

    Declara en el router qué permiso pide cada endpoint. Una clave fuera del catálogo falla al
    importar el módulo, no en producción.
    """
    if not es_clave_valida(clave):
        raise ValueError(f"Permiso desconocido: {clave!r}. Agrégalo a acceso/permisos.py")

    def dependencia(usuario: UsuarioActual, service: AccesoServiceDep) -> Usuario:
        if not service.tiene_permiso(usuario, clave):
            raise SinPermiso()
        return usuario

    dependencia.__name__ = f"requiere_{clave.replace('.', '_')}"
    return dependencia
