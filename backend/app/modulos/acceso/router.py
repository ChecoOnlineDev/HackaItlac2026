"""Endpoints de sesión (US-ACC-001, AC-14 a AC-24). Usuarios y personal: `router_usuarios.py`."""

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.handlers import respuesta_error
from app.modulos.acceso.dependencies import AccesoServiceDep, FamiliaActual, UsuarioActual
from app.modulos.acceso.exceptions import SesionVencida
from app.modulos.acceso.router_almacenes_usuario import router as router_almacenes_usuario
from app.modulos.acceso.router_roles import router as router_roles
from app.modulos.acceso.router_usuarios import router as router_usuarios
from app.modulos.acceso.schemas import CerradasOut, DispositivosOut, LoginIn, SesionOut
from app.modulos.acceso.service_sesiones import SesionEmitida
from app.seguridad import (
    poner_cookie_acceso,
    poner_cookie_refresh,
    quitar_cookies_sesion,
)

router = APIRouter(tags=["acceso"])
router.include_router(router_usuarios)
router.include_router(router_roles)
router.include_router(router_almacenes_usuario)


def _agente(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _poner_cookies(response: Response, emitida: SesionEmitida) -> None:
    poner_cookie_acceso(response, emitida.token_acceso)
    if emitida.token_refresh is not None:  # dentro de la tolerancia no se toca la de renovación
        poner_cookie_refresh(response, emitida.token_refresh, emitida.refresh_segundos)


@router.post("/sesion", response_model=SesionOut)
def iniciar_sesion(
    datos: LoginIn, request: Request, response: Response, service: AccesoServiceDep
) -> SesionOut:
    """Público. Entra con usuario y contraseña; abre la sesión de este dispositivo y deja las
    cookies de acceso y de renovación."""
    ajustes = get_settings()
    emitida = service.iniciar_sesion(
        datos.usuario,
        datos.contrasena,
        _agente(request),
        request.cookies.get(ajustes.cookie_refresh_nombre),
    )
    _poner_cookies(response, emitida)
    return service.construir_sesion(emitida.usuario)


@router.post("/sesion/refresh", response_model=SesionOut)
def renovar_sesion(
    request: Request, response: Response, service: AccesoServiceDep
) -> SesionOut | JSONResponse:
    """Público (la identifica el token de renovación, no el de acceso). Rota el token de
    renovación y da un token de acceso nuevo. Si no sirve: 401 `SESION_VENCIDA` y borra las
    cookies."""
    ajustes = get_settings()
    try:
        emitida = service.renovar_sesion(
            request.cookies.get(ajustes.cookie_refresh_nombre), _agente(request)
        )
    except SesionVencida as exc:
        fallo = respuesta_error(401, exc.codigo, exc.mensaje, exc.detalles)
        quitar_cookies_sesion(fallo)
        return fallo
    _poner_cookies(response, emitida)
    return service.construir_sesion(emitida.usuario)


@router.get("/sesion", response_model=SesionOut)
def ver_sesion(usuario: UsuarioActual, service: AccesoServiceDep) -> SesionOut:
    """Sesión. Usuario, rol, almacén y permisos, para armar menús y botones."""
    return service.construir_sesion(usuario)


@router.delete("/sesion", status_code=status.HTTP_204_NO_CONTENT)
def cerrar_sesion(
    usuario: UsuarioActual, familia_id: FamiliaActual, service: AccesoServiceDep
) -> Response:
    """Sesión. Cierra SOLO la sesión de este dispositivo y borra las cookies; las de los demás
    dispositivos siguen abiertas."""
    service.cerrar_sesion(usuario, familia_id)
    respuesta = Response(status_code=status.HTTP_204_NO_CONTENT)
    quitar_cookies_sesion(respuesta)
    return respuesta


@router.delete("/sesion/todas", status_code=status.HTTP_204_NO_CONTENT)
def cerrar_todas_las_sesiones(usuario: UsuarioActual, service: AccesoServiceDep) -> Response:
    """Sesión. Cierra las sesiones de TODOS los dispositivos del usuario, también este."""
    service.cerrar_todas_las_sesiones(usuario)
    respuesta = Response(status_code=status.HTTP_204_NO_CONTENT)
    quitar_cookies_sesion(respuesta)
    return respuesta


@router.delete("/sesion/otras", response_model=CerradasOut)
def cerrar_otras_sesiones(
    usuario: UsuarioActual, familia_id: FamiliaActual, service: AccesoServiceDep
) -> CerradasOut:
    """Sesión. Cierra las sesiones de los demás dispositivos y deja abierta la de este."""
    return CerradasOut(cerradas=service.cerrar_otras_sesiones(usuario, familia_id))


@router.get("/sesion/dispositivos", response_model=DispositivosOut)
def ver_dispositivos(
    usuario: UsuarioActual, familia_id: FamiliaActual, service: AccesoServiceDep
) -> DispositivosOut:
    """Sesión. Los dispositivos con sesión abierta del usuario y cuál es este."""
    return service.dispositivos(usuario, familia_id)
