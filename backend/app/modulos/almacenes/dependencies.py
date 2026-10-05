"""Dependencias de FastAPI del módulo `almacenes`."""

from typing import Annotated

from fastapi import Depends

from app.db import SesionDep
from app.modulos.almacenes.service import AlmacenService


def get_almacen_service(session: SesionDep) -> AlmacenService:
    return AlmacenService(session)


AlmacenServiceDep = Annotated[AlmacenService, Depends(get_almacen_service)]
