"""Comprobante público por token aleatorio y reporte reservado de integridad."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.schemas import FechaUtc
from app.modulos.consulta.service_comprobante import ComprobanteService

router = APIRouter(tags=["comprobantes"])


class TrabajadorPublicoOut(BaseModel):
    nombre: str
    numero_empleado: str


class ArticuloPublicoOut(BaseModel):
    renglon: int
    codigo: str
    nombre: str
    marca: str | None
    modelo: str | None
    talla: str | None
    numero_serie: str | None
    cantidad: int
    condicion: str | None


class ComprobantePublicoOut(BaseModel):
    folio: str
    creado_en: FechaUtc
    integridad: str
    regla: str
    trabajador: TrabajadorPublicoOut | None
    articulos: list[ArticuloPublicoOut] = Field(default_factory=list)


@router.get("/publico/vales/{token}", response_model=ComprobantePublicoOut)
def publico(token: str, session: SesionDep):
    return ComprobanteService(session).publico(token)


@router.get("/reportes/integridad")
def integridad(
    session: SesionDep,
    actor: Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_MOVIMIENTOS))],
    almacen_id: uuid.UUID | None = None,
):
    return ComprobanteService(session).integridad(actor, almacen_id)
