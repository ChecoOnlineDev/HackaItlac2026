"""CP-04/C-09: permisos explícitos por clave y lectura histórica de almacenes cerrados."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.dependencies import ValorServiceDep
from app.modulos.consulta.schemas_cierre import CierreFilters, CierreOut
from app.modulos.consulta.schemas_tablero import ValorInventarioOut
from app.modulos.consulta.service_cierre import CierreService

router = APIRouter(tags=["consulta"])


@router.get("/almacenes/{almacen_id}/reporte-cierre", response_model=CierreOut)
def cierre(
    almacen_id: uuid.UUID,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_CIERRE))],
    session: SesionDep,
    filtros: Annotated[CierreFilters, Query()],
):
    return CierreService(session).consultar(usuario, almacen_id, filtros)


@router.get("/reportes/valor-inventario", response_model=ValorInventarioOut)
def valor(
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.REPORTES_VALOR_INVENTARIO))],
    service: ValorServiceDep,
    almacen_id: uuid.UUID | None = None,
):
    return service.valor(usuario, almacen_id)
