"""Dependencias de FastAPI del módulo `catalogo`."""

from typing import Annotated

from fastapi import Depends

from app.db import SesionDep
from app.modulos.catalogo.service import CatalogoService
from app.modulos.catalogo.service_puestos import PuestoService
from app.modulos.catalogo.service_series import SerieService


def get_catalogo_service(session: SesionDep) -> CatalogoService:
    return CatalogoService(session)


def get_puesto_service(session: SesionDep) -> PuestoService:
    return PuestoService(session)


def get_serie_service(session: SesionDep) -> SerieService:
    return SerieService(session)


CatalogoServiceDep = Annotated[CatalogoService, Depends(get_catalogo_service)]
PuestoServiceDep = Annotated[PuestoService, Depends(get_puesto_service)]
SerieServiceDep = Annotated[SerieService, Depends(get_serie_service)]
