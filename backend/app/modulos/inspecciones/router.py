"""Endpoints del módulo `inspecciones`: /piezas/{id}/inspecciones, /estado y /ajuste-vigencia.

Router delgado: cada endpoint declara su permiso y delega en `InspeccionService`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.inspecciones.schemas import (
    AjusteVigenciaIn,
    AjusteVigenciaOut,
    EstadoCambiadoOut,
    InspeccionCreate,
    InspeccionOut,
    MarcarNoAptaIn,
)
from app.modulos.inspecciones.service import InspeccionService

router = APIRouter(prefix="/piezas", tags=["inspecciones"])


def get_inspeccion_service(session: SesionDep) -> InspeccionService:
    return InspeccionService(session)


ServiceDep = Annotated[InspeccionService, Depends(get_inspeccion_service)]


@router.post(
    "/{pieza_id}/inspecciones", response_model=InspeccionOut, status_code=status.HTTP_201_CREATED
)
def inspeccionar(
    pieza_id: uuid.UUID,
    datos: InspeccionCreate,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.PIEZAS_INSPECCIONAR))],
    service: ServiceDep,
) -> InspeccionOut:
    """`piezas.inspeccionar`. Registra una inspección (P-01)."""
    return service.registrar(pieza_id, datos, usuario)


@router.post("/{pieza_id}/estado", response_model=EstadoCambiadoOut)
def marcar_no_apta(
    pieza_id: uuid.UUID,
    datos: MarcarNoAptaIn,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.PIEZAS_INSPECCIONAR))],
    service: ServiceDep,
) -> EstadoCambiadoOut:
    """`piezas.inspeccionar`. Marca la pieza No apta, con observación (P-03)."""
    return service.marcar_no_apta(pieza_id, datos, usuario)


@router.post(
    "/{pieza_id}/ajuste-vigencia",
    response_model=AjusteVigenciaOut,
    status_code=status.HTTP_201_CREATED,
)
def ajustar_vigencia(
    pieza_id: uuid.UUID,
    datos: AjusteVigenciaIn,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.PIEZAS_AJUSTAR_VIGENCIA))],
    service: ServiceDep,
) -> AjusteVigenciaOut:
    """`piezas.ajustar_vigencia`. Cambia la fecha hasta la que vale la inspección (P-07)."""
    return service.ajustar_vigencia(pieza_id, datos, usuario)
