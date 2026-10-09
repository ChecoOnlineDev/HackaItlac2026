import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.dependencies import requiere_alguno
from app.modulos.consulta.schemas_bitacora import BitacoraFilters
from app.modulos.consulta.service_bitacora import BitacoraService

router = APIRouter(tags=["bitacora"])


@router.get("/bitacora")
def bitacora(
    session: SesionDep,
    usuario: Annotated[Usuario, Depends(requiere_alguno(P.BITACORA_VER, P.REPORTES_MOVIMIENTOS))],
    filtros: Annotated[BitacoraFilters, Depends()],
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=200)] = 25,
    formato: Literal["json", "csv"] = "json",
):
    return BitacoraService(session).consultar(usuario, filtros, pagina, tamano, formato)


@router.get("/vales/{vale_id}/renglones")
def renglones(
    vale_id: uuid.UUID,
    session: SesionDep,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.VALES_VER))],
    q: Annotated[str, Query(max_length=100)] = "",
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=500)] = 50,
):
    return BitacoraService(session).renglones(vale_id, usuario, q, pagina, tamano)
