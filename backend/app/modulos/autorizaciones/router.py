"""Endpoints del modulo `autorizaciones`: solicitud y resolucion de autorizaciones.

Router delgado: cada endpoint declara su permiso y delega en `AutorizacionService`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.paginacion import Pagina, PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import UsuarioActual, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.autorizaciones.models import EstadoAutorizacion
from app.modulos.autorizaciones.schemas import (
    AutorizacionOut,
    ResolucionIn,
    SolicitudCreada,
    SolicitudCreate,
    SolicitudListItem,
)
from app.modulos.autorizaciones.service import AutorizacionService

router = APIRouter(prefix="/autorizaciones", tags=["autorizaciones"])


def get_autorizacion_service(session: SesionDep) -> AutorizacionService:
    return AutorizacionService(session)


ServiceDep = Annotated[AutorizacionService, Depends(get_autorizacion_service)]


@router.post("", response_model=SolicitudCreada, status_code=status.HTTP_201_CREATED)
def solicitar(
    datos: SolicitudCreate,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.ENTREGAS_CREAR))],
    service: ServiceDep,
) -> SolicitudCreada:
    """`entregas.crear`. Pide autorización al supervisor con un motivo (A-02)."""
    autorizacion = service.solicitar(usuario, datos)
    return SolicitudCreada(
        id=autorizacion.id, estado=autorizacion.estado, vence_en=autorizacion.vence_en
    )


@router.get("", response_model=Pagina[SolicitudListItem])
def listar(
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.AUTORIZACIONES_RESOLVER))],
    service: ServiceDep,
    paginacion: PaginacionDep,
    estado: Annotated[EstadoAutorizacion | None, Query()] = EstadoAutorizacion.PENDIENTE,
) -> Pagina[SolicitudListItem]:
    """`autorizaciones.resolver`. Solicitudes por resolver de su almacén (o de todos)."""
    elementos, total = service.listar(usuario, estado, paginacion)
    return Pagina(elementos=elementos, total=total)


@router.get("/{autorizacion_id}", response_model=AutorizacionOut)
def ver(autorizacion_id: uuid.UUID, usuario: UsuarioActual, service: ServiceDep) -> AutorizacionOut:
    """Sesión. La ve quien la pidió y quien puede resolverla; si venció, informa VENCIDA."""
    return service.consultar(autorizacion_id, usuario)


@router.post("/{autorizacion_id}/resolucion", response_model=AutorizacionOut)
def resolver(
    autorizacion_id: uuid.UUID,
    datos: ResolucionIn,
    usuario: UsuarioActual,
    service: ServiceDep,
) -> AutorizacionOut:
    """`autorizaciones.resolver`: de quien tiene la sesión, o del usuario que da su PIN.

    El permiso se verifica en el service porque, con PIN, se verifica sobre el usuario
    identificado y no sobre quien tiene la sesión (el almacenista).
    """
    return service.resolver(autorizacion_id, usuario, datos)
