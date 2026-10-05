"""Dependencias de FastAPI del módulo `catalogo`."""

from typing import Annotated

from fastapi import Depends

from app.db import SesionDep
from app.modulos.catalogo.service import CatalogoService


def get_catalogo_service(session: SesionDep) -> CatalogoService:
    return CatalogoService(session)


CatalogoServiceDep = Annotated[CatalogoService, Depends(get_catalogo_service)]
