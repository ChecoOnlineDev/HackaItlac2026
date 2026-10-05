"""Endpoints de sesión (US-ACC-001). Usuarios y personal: `router_usuarios.py`."""

from fastapi import APIRouter, Response, status

from app.modulos.acceso.dependencies import AccesoServiceDep, UsuarioActual
from app.modulos.acceso.router_usuarios import router as router_usuarios
from app.modulos.acceso.schemas import LoginIn, SesionOut
from app.seguridad import crear_token, poner_cookie_sesion, quitar_cookie_sesion

router = APIRouter(tags=["acceso"])
router.include_router(router_usuarios)


@router.post("/sesion", response_model=SesionOut)
def iniciar_sesion(datos: LoginIn, response: Response, service: AccesoServiceDep) -> SesionOut:
    """Público. Entra con usuario y contraseña; deja la cookie de sesión."""
    usuario = service.autenticar(datos.usuario, datos.contrasena)
    poner_cookie_sesion(response, crear_token(usuario.id, usuario.version_sesion))
    return service.construir_sesion(usuario)


@router.get("/sesion", response_model=SesionOut)
def ver_sesion(usuario: UsuarioActual, service: AccesoServiceDep) -> SesionOut:
    """Sesión. Usuario, rol, almacén y permisos, para armar menús y botones."""
    return service.construir_sesion(usuario)


@router.delete("/sesion", status_code=status.HTTP_204_NO_CONTENT)
def cerrar_sesion(usuario: UsuarioActual, service: AccesoServiceDep) -> Response:
    """Sesión. Sale y revoca el token: cierra la sesión en todos los dispositivos del usuario."""
    service.cerrar_sesiones(usuario)
    respuesta = Response(status_code=status.HTTP_204_NO_CONTENT)
    quitar_cookie_sesion(respuesta)
    return respuesta
