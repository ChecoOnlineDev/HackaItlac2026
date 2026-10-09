"""Endpoints del módulo `almacenes`: la red, las existencias (`inventario.ver`) y la
administración de almacenes (`almacenes.administrar`, FEAT-008)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.core.excepciones import SinPermiso
from app.core.paginacion import PaginacionDep
from app.modulos.acceso.dependencies import AccesoServiceDep, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.dependencies import AlmacenServiceDep
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado
from app.modulos.almacenes.router_minimos import router as router_minimos
from app.modulos.almacenes.schemas import (
    AlmacenCreate,
    AlmacenFilters,
    AlmacenOut,
    AlmacenUpdate,
    AutonomiaAlmacenIn,
    CambioEstadoIn,
    ExistenciasOut,
)

router = APIRouter(prefix="/almacenes", tags=["almacenes"])


router.include_router(router_minimos)


UsuarioInventario = Annotated[Usuario, Depends(requiere_permiso(P.INVENTARIO_VER))]
UsuarioAdministrar = Annotated[Usuario, Depends(requiere_permiso(P.ALMACENES_ADMINISTRAR))]
UsuarioAutonomia = Annotated[Usuario, Depends(requiere_permiso(P.DESPACHO_AUTONOMIA))]


@router.patch("/{almacen_id}/autonomia", response_model=AlmacenOut)
def cambiar_autonomia(
    almacen_id: uuid.UUID,
    datos: AutonomiaAlmacenIn,
    usuario: UsuarioAutonomia,
    service: AlmacenServiceDep,
) -> AlmacenOut:
    return service.cambiar_autonomia(almacen_id, datos, usuario)


@router.get("", response_model=list[AlmacenOut])
def listar_almacenes(
    usuario: UsuarioInventario,
    service: AlmacenServiceDep,
    acceso: AccesoServiceDep,
    resumen: bool = False,
) -> list[AlmacenOut]:
    """`inventario.ver`. Los almacenes con su red: quién los surte y a quién surten.

    AC-06: con `almacenes.todos` o `traspasos.operar` (quien necesita los destinos de un traspaso:
    solo su nombre y clave, nunca su inventario) vienen todos; los demás ven solo el suyo.
    `resumen=true` agrega existencias, usuarios y bloqueos de cierre de cada almacén: solo con
    `almacenes.administrar` (trae datos de otros almacenes).
    """
    permisos = acceso.permisos_de(usuario)
    if resumen and P.ALMACENES_ADMINISTRAR not in permisos:
        raise SinPermiso()
    almacenes = service.listar(resumen=resumen)
    if P.ALMACENES_TODOS in permisos or P.TRASPASOS_OPERAR in permisos:
        return almacenes
    asignados = acceso.almacenes_del_usuario(usuario.id)
    return [a for a in almacenes if a.id in asignados]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AlmacenOut)
def crear_almacen(
    datos: AlmacenCreate, usuario: UsuarioAdministrar, service: AlmacenServiceDep
) -> AlmacenOut:
    """`almacenes.administrar`. Alta (AL-01, AL-02): crea el almacén y su ubicación."""
    return service.crear(datos, usuario)


@router.patch("/{almacen_id}", response_model=AlmacenOut)
def editar_almacen(
    almacen_id: uuid.UUID,
    datos: AlmacenUpdate,
    usuario: UsuarioAdministrar,
    service: AlmacenServiceDep,
) -> AlmacenOut:
    """`almacenes.administrar`. Nombre, de quién depende y, sin folios, la clave (AL-05)."""
    return service.editar(almacen_id, datos, usuario)


@router.post("/{almacen_id}/cierre", response_model=AlmacenOut)
def cerrar_almacen(
    almacen_id: uuid.UUID,
    usuario: UsuarioAdministrar,
    service: AlmacenServiceDep,
    datos: Annotated[CambioEstadoIn | None, Body()] = None,
) -> AlmacenOut:
    """`almacenes.administrar`. Inactiva el almacén si cumple las condiciones de AL-03."""
    return service.cerrar(almacen_id, datos, usuario)


@router.post("/{almacen_id}/reapertura", response_model=AlmacenOut)
def reabrir_almacen(
    almacen_id: uuid.UUID,
    usuario: UsuarioAdministrar,
    service: AlmacenServiceDep,
    datos: Annotated[CambioEstadoIn | None, Body()] = None,
) -> AlmacenOut:
    """`almacenes.administrar`. Reactiva el mismo almacén (AL-03)."""
    return service.reabrir(almacen_id, datos, usuario)


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
    if not acceso.en_alcance(usuario, almacen_id):
        raise AlmacenNoEncontrado()
    return service.existencias(almacen_id, filtros, pagina)
