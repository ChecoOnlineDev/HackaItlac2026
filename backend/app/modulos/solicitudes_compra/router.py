"""Endpoints del módulo `solicitudes_compra`: la solicitud de compra urgente y su seguimiento.

Router delgado: cada endpoint declara su permiso y delega en `SolicitudCompraService`. Excepción
documentada: `GET /api/solicitudes-compra` y `GET /api/solicitudes-compra/{id}` aceptan
`compras.solicitar` o `compras.atender`; como el router solo declara un permiso por ruta, ahí exige
sesión y el servicio verifica cualquiera de los dos (403 `SIN_PERMISO` si no tiene ninguno).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.paginacion import Pagina, PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import UsuarioActual, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.solicitudes_compra.schemas import (
    CambioEstadoIn,
    CancelacionIn,
    ConteoOut,
    FiltrosSolicitudes,
    SolicitudCreate,
    SolicitudDetalleOut,
    SolicitudOut,
)
from app.modulos.solicitudes_compra.service import SolicitudCompraService

router = APIRouter(prefix="/solicitudes-compra", tags=["solicitudes-compra"])


def get_service(session: SesionDep) -> SolicitudCompraService:
    return SolicitudCompraService(session)


ServiceDep = Annotated[SolicitudCompraService, Depends(get_service)]

Solicitar = Annotated[Usuario, Depends(requiere_permiso(P.COMPRAS_SOLICITAR))]
Atender = Annotated[Usuario, Depends(requiere_permiso(P.COMPRAS_ATENDER))]


@router.post("", response_model=SolicitudDetalleOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: SolicitudCreate, usuario: Solicitar, service: ServiceDep, response: Response
) -> SolicitudDetalleOut:
    """`compras.solicitar`. Levanta una solicitud de compra urgente (SC-01, SC-02). 201; 200 con la
    misma solicitud si el `id_cliente` ya existía con el mismo cuerpo (SC-10)."""
    solicitud, creada = service.crear(usuario, datos)
    if not creada:
        response.status_code = status.HTTP_200_OK
    return solicitud


@router.get("", response_model=Pagina[SolicitudOut] | ConteoOut)
def listar(
    usuario: UsuarioActual,
    service: ServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[FiltrosSolicitudes, Query()],
) -> Pagina[SolicitudOut] | ConteoOut:
    """`compras.solicitar` o `compras.atender` (verificado en el servicio). Quien atiende ve las de
    todos los almacenes; los demás, las de su almacén (SC-03). `solo_contar=true` responde
    `{total}`."""
    return service.listar(usuario, filtros, pagina)


@router.get("/{solicitud_id}", response_model=SolicitudDetalleOut)
def ver(
    solicitud_id: uuid.UUID, usuario: UsuarioActual, service: ServiceDep
) -> SolicitudDetalleOut:
    """`compras.solicitar` o `compras.atender` (verificado en el servicio). Detalle con su línea
    de tiempo y las acciones que el usuario puede hacer."""
    return service.detalle(usuario, solicitud_id)


@router.post("/{solicitud_id}/estado", response_model=SolicitudDetalleOut)
def cambiar_estado(
    solicitud_id: uuid.UUID, datos: CambioEstadoIn, usuario: Atender, service: ServiceDep
) -> SolicitudDetalleOut:
    """`compras.atender`. Tomar, rechazar, marcar comprada o ingresar (SC-04 a SC-06)."""
    return service.cambiar_estado(usuario, solicitud_id, datos)


@router.post("/{solicitud_id}/cancelacion", response_model=SolicitudDetalleOut)
def cancelar(
    solicitud_id: uuid.UUID,
    usuario: Solicitar,
    service: ServiceDep,
    datos: CancelacionIn | None = None,
) -> SolicitudDetalleOut:
    """`compras.solicitar`. Cancela una solicitud PENDIENTE: quien la pidió, un supervisor de su
    almacén o el Administrador (SC-07). El cuerpo es opcional."""
    return service.cancelar(usuario, solicitud_id, datos or CancelacionIn())
