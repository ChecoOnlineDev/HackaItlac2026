"""DU-01/07/08: rutas de lectura, permisos explícitos por acción."""

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.schemas_deudores import DeudoresFilters
from app.modulos.consulta.service_consumo_trabajador import ConsumoTrabajadorService
from app.modulos.consulta.service_deudores import DeudoresService

router = APIRouter(tags=["deudores"])
VerDeudores = Annotated[Usuario, Depends(requiere_permiso(P.DEUDORES_VER))]
Filtros = Annotated[DeudoresFilters, Depends()]


@router.get("/deudores")
def listado(
    session: SesionDep,
    usuario: VerDeudores,
    filtros: Filtros,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=200)] = 50,
    formato: Literal["json", "csv"] = "json",
):
    return DeudoresService(session).consultar(
        usuario, filtros.model_dump(), pagina, tamano, formato
    )


@router.get("/deudores/resumen")
def resumen(
    session: SesionDep,
    usuario: VerDeudores,
    filtros: Filtros,
    formato: Literal["json", "csv"] = "json",
):
    return DeudoresService(session).resumen(usuario, filtros.model_dump(), formato)


@router.get("/trabajadores/{trabajador_id}/consumo")
def consumo(
    trabajador_id: uuid.UUID,
    session: SesionDep,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.TRABAJADORES_VER))],
    desde: date | None = None,
    hasta: date | None = None,
):
    return ConsumoTrabajadorService(session).consultar(trabajador_id, usuario, desde, hasta)
