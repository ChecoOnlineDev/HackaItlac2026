import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from app.config import get_settings
from app.core.excepciones import NoEncontrado
from app.db import SesionDep
from app.modulos.acceso.dependencies import FamiliaActual, UsuarioActual, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.notificaciones.schemas import (
    ClavePublicaOut,
    PruebaOut,
    SuscripcionIn,
    SuscripcionOut,
)
from app.modulos.notificaciones.service import NotificacionService

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])
Supervisor = Annotated[Usuario, Depends(requiere_permiso(P.AUTORIZACIONES_RESOLVER))]


@router.get("/clave-publica", response_model=ClavePublicaOut)
def clave_publica(usuario: UsuarioActual):
    clave = get_settings().vapid_clave_publica
    if not clave:
        raise NoEncontrado("Las notificaciones aún no están configuradas.")
    return ClavePublicaOut(clave_publica=clave)


@router.post("/suscripciones", response_model=SuscripcionOut, status_code=201)
def registrar(
    datos: SuscripcionIn,
    usuario: Supervisor,
    familia: FamiliaActual,
    session: SesionDep,
    response: Response,
    user_agent: Annotated[str | None, Header()] = None,
):
    s, repetida = NotificacionService(session).registrar(usuario, familia, datos, user_agent)
    response.status_code = 200 if repetida else 201
    return SuscripcionOut(id=s.id, creada_en=s.creada_en)


@router.delete("/suscripciones/{id}", status_code=204)
def revocar(id: uuid.UUID, usuario: UsuarioActual, familia: FamiliaActual, session: SesionDep):
    NotificacionService(session).revocar(id, usuario, familia)


@router.post("/prueba", response_model=PruebaOut)
def prueba(usuario: Supervisor, familia: FamiliaActual, session: SesionDep):
    return NotificacionService(session).prueba(usuario, familia)
