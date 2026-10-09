import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.schemas_minimos import MinimoOut, MinimosIn
from app.modulos.almacenes.service_minimos import MinimosService

router = APIRouter()
UsuarioMinimos = Annotated[Usuario, Depends(requiere_permiso(P.INVENTARIO_MINIMOS))]


@router.get("/{almacen_id}/minimos", response_model=list[MinimoOut])
def listar_minimos(almacen_id: uuid.UUID, usuario: UsuarioMinimos, session: SesionDep):
    return MinimosService(session).listar(almacen_id, usuario)


@router.put("/{almacen_id}/minimos", response_model=list[MinimoOut])
def configurar_minimos(
    almacen_id: uuid.UUID, datos: MinimosIn, usuario: UsuarioMinimos, session: SesionDep
):
    return MinimosService(session).cambiar(almacen_id, datos, usuario)
