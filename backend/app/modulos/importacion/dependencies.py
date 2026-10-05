"""Dependencias de FastAPI del módulo `importacion`."""

from typing import Annotated

from fastapi import Depends

from app.db import SesionDep
from app.modulos.importacion.service import ImportacionService


def get_importacion_service(session: SesionDep) -> ImportacionService:
    return ImportacionService(session)


ImportacionServiceDep = Annotated[ImportacionService, Depends(get_importacion_service)]
