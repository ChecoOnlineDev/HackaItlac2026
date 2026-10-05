"""Dependencias de FastAPI del módulo `consulta`."""

from typing import Annotated

from fastapi import Depends

from app.db import SesionDep
from app.modulos.consulta.service import ConsultaService


def get_consulta_service(session: SesionDep) -> ConsultaService:
    return ConsultaService(session)


ConsultaServiceDep = Annotated[ConsultaService, Depends(get_consulta_service)]
