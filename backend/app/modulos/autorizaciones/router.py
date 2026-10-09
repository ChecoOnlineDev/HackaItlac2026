"""Endpoints del modulo `autorizaciones`: solicitud y resolucion de autorizaciones.

Router delgado: cada endpoint declara su permiso y delega en `AutorizacionService`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.core.paginacion import Pagina, PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import FamiliaActual, UsuarioActual, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.autorizaciones.models import EstadoAutorizacion, TipoAutorizacion
from app.modulos.autorizaciones.schemas import (
    AutorizacionOut,
    ResolucionIn,
    ResolucionMultipleIn,
    ResolucionMultipleOut,
    SolicitudCreada,
    SolicitudCreate,
    SolicitudListItem,
)
from app.modulos.autorizaciones.service import AutorizacionService
from app.modulos.movimientos.verificador import crear_verificador, crear_verificador_traslado
from app.modulos.notificaciones.service import enviar_aviso_autorizacion

router = APIRouter(prefix="/autorizaciones", tags=["autorizaciones"])


def get_autorizacion_service(session: SesionDep) -> AutorizacionService:
    return AutorizacionService(session)


ServiceDep = Annotated[AutorizacionService, Depends(get_autorizacion_service)]


@router.post("", response_model=SolicitudCreada, status_code=status.HTTP_201_CREATED)
def solicitar(
    datos: SolicitudCreate,
    usuario: UsuarioActual,
    service: ServiceDep,
    response: Response,
    tareas: BackgroundTasks,
) -> SolicitudCreada:
    """Sesión; el servicio verifica el permiso según el `tipo`: `entregas.crear` para un
    EXCEDENTE y `traspasos.operar` para un TRASLADO. Pide autorización al supervisor con un
    motivo (A-02)."""
    # A-06: `movimientos` rechaza los renglones en rojo con su evaluación real.
    autorizacion = service.solicitar(
        usuario,
        datos,
        verificador_renglones=crear_verificador(service.session, usuario),
        verificador_traslado=crear_verificador_traslado(service.session, usuario),
    )
    response.status_code = 200 if service.repetida else 201
    if not service.repetida:
        tareas.add_task(enviar_aviso_autorizacion, autorizacion.id)
    return SolicitudCreada(
        id=autorizacion.id,
        tipo=autorizacion.tipo,
        estado=autorizacion.estado,
        vence_en=autorizacion.vence_en,
        avisados=(autorizacion.detalle or {}).get("avisados", 0),
    )


@router.get("", response_model=Pagina[SolicitudListItem])
def listar(
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.AUTORIZACIONES_RESOLVER))],
    service: ServiceDep,
    paginacion: PaginacionDep,
    estado: Annotated[EstadoAutorizacion | None, Query()] = EstadoAutorizacion.PENDIENTE,
    tipo: Annotated[TipoAutorizacion | None, Query()] = None,
    almacen_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Pagina[SolicitudListItem]:
    """`autorizaciones.resolver`. Solicitudes por resolver de su almacén (o de todos); `tipo`
    filtra entre excedentes y traslados."""
    elementos, total = service.listar(usuario, estado, paginacion, tipo, almacen_id)
    return Pagina(elementos=elementos, total=total)


@router.post("/resolucion-multiple", response_model=ResolucionMultipleOut)
def resolver_multiple(
    datos: ResolucionMultipleIn,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.AUTORIZACIONES_RESOLVER))],
    service: ServiceDep,
    familia: FamiliaActual,
    tareas: BackgroundTasks,
):
    salida = service.resolver_multiple(usuario, datos)
    for resultado in salida.resultados:
        if resultado.estado in (EstadoAutorizacion.APROBADA, EstadoAutorizacion.RECHAZADA):
            tareas.add_task(enviar_aviso_autorizacion, resultado.id, "RESUELTA", familia)
    return salida


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
    familia: FamiliaActual,
    tareas: BackgroundTasks,
) -> AutorizacionOut:
    """`autorizaciones.resolver`: de quien tiene la sesión, o del usuario que da su PIN.

    El permiso se verifica en el service porque, con PIN, se verifica sobre el usuario
    identificado y no sobre quien tiene la sesión (el almacenista). Un TRASLADO solo lo resuelve
    el supervisor de su origen (X-19): para los demás, 404.
    """
    salida = service.resolver(autorizacion_id, usuario, datos)
    tareas.add_task(enviar_aviso_autorizacion, autorizacion_id, "RESUELTA", familia)
    return salida
