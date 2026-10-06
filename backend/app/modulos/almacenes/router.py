"""Endpoints del módulo `almacenes`: la red y las existencias (`inventario.ver`)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.paginacion import PaginacionDep
from app.modulos.acceso.dependencies import AccesoServiceDep, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.dependencies import AlmacenServiceDep
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado
from app.modulos.almacenes.schemas import AlmacenFilters, AlmacenOut, ExistenciasOut

router = APIRouter(prefix="/almacenes", tags=["almacenes"])


UsuarioInventario = Annotated[Usuario, Depends(requiere_permiso(P.INVENTARIO_VER))]


@router.get("", response_model=list[AlmacenOut])
def listar_almacenes(
    usuario: UsuarioInventario, service: AlmacenServiceDep, acceso: AccesoServiceDep
) -> list[AlmacenOut]:
    """`inventario.ver`. Los almacenes con su red: quién los surte y a quién surten.

    AC-06: con `almacenes.todos` o `traspasos.operar` (quien necesita los destinos de un traspaso:
    solo su nombre y clave, nunca su inventario) vienen todos; los demás ven solo el suyo.
    """
    almacenes = service.listar()
    permisos = acceso.permisos_de(usuario)
    if P.ALMACENES_TODOS in permisos or P.TRASPASOS_OPERAR in permisos:
        return almacenes
    return [a for a in almacenes if a.id == usuario.almacen_id]


@router.get("/{almacen_id}/existencias", response_model=ExistenciasOut)
def existencias_del_almacen(
    almacen_id: uuid.UUID,
    usuario: UsuarioInventario,
    acceso: AccesoServiceDep,
    service: AlmacenServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[AlmacenFilters, Query()],
) -> ExistenciasOut:
    """`inventario.ver`. Existencias y disponibles por artículo (sin costos).

    AC-06: sin `almacenes.todos`, solo las del almacén asignado; las de otro, como si no existiera.
    """
    if not acceso.puede_operar_todos_los_almacenes(usuario) and almacen_id != usuario.almacen_id:
        raise AlmacenNoEncontrado()
    return service.existencias(almacen_id, filtros, pagina)
