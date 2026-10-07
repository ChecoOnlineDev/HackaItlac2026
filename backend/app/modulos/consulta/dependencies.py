"""Dependencias de FastAPI del módulo `consulta`."""

from typing import Annotated

from fastapi import Depends

from app.db import SesionDep
from app.modulos.consulta.service import ConsultaService
from app.modulos.consulta.service_seguimiento import SeguimientoService
from app.modulos.consulta.service_tablero import TableroService


def get_consulta_service(session: SesionDep) -> ConsultaService:
    return ConsultaService(session)


ConsultaServiceDep = Annotated[ConsultaService, Depends(get_consulta_service)]


def get_seguimiento_service(session: SesionDep) -> SeguimientoService:
    return SeguimientoService(session)


SeguimientoServiceDep = Annotated[SeguimientoService, Depends(get_seguimiento_service)]


def get_tablero_service(session: SesionDep) -> TableroService:
    return TableroService(session)


TableroServiceDep = Annotated[TableroService, Depends(get_tablero_service)]
