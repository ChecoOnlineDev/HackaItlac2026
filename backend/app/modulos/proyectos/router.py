"""API de proyectos y asignaciones; autorización explícita en cada endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.paginacion import Pagina, PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.consulta.dependencies import requiere_alguno
from app.modulos.proyectos.schemas import (
    AsignacionIn,
    AsignacionOut,
    CierreIn,
    CierreOut,
    ProyectoCreate,
    ProyectoOut,
    ProyectoUpdate,
    ReaperturaIn,
    Situacion,
    TerminoOut,
)
from app.modulos.proyectos.service import ProyectoService

router = APIRouter(tags=["proyectos"])


def get_service(session: SesionDep):
    return ProyectoService(session)


ServiceDep = Annotated[ProyectoService, Depends(get_service)]
Lector = Annotated[Usuario, Depends(requiere_alguno("proyectos.ver", "proyectos.asignar"))]
Administrador = Annotated[Usuario, Depends(requiere_permiso("proyectos.administrar"))]
Asignador = Annotated[Usuario, Depends(requiere_permiso("proyectos.asignar"))]
LectorTrabajador = Annotated[Usuario, Depends(requiere_permiso("trabajadores.ver"))]


@router.get("/proyectos", response_model=Pagina[ProyectoOut])
def listar(
    usuario: Lector,
    service: ServiceDep,
    pagina: PaginacionDep,
    almacen_id: uuid.UUID | None = None,
    situacion: Situacion | None = None,
    q: str | None = None,
    asignables: bool = False,
    por_vencer: bool = False,
):
    return service.listar(
        usuario,
        pagina,
        almacen_id=almacen_id,
        situacion=situacion,
        q=q,
        asignables=asignables,
        por_vencer=por_vencer,
    )


@router.post("/proyectos", status_code=201, response_model=ProyectoOut)
def crear(datos: ProyectoCreate, usuario: Administrador, service: ServiceDep):
    return service.crear(datos, usuario)


@router.get("/proyectos/{id}", response_model=ProyectoOut)
def detalle(id: uuid.UUID, usuario: Lector, service: ServiceDep):
    return service.ficha(service.obtener(id, usuario))


@router.patch("/proyectos/{id}", response_model=ProyectoOut)
def editar(id: uuid.UUID, datos: ProyectoUpdate, usuario: Administrador, service: ServiceDep):
    return service.editar(id, datos, usuario)


@router.post("/proyectos/{id}/cierre", response_model=CierreOut)
def cerrar(id: uuid.UUID, datos: CierreIn, usuario: Administrador, service: ServiceDep):
    return service.cerrar(id, datos, usuario)


@router.post("/proyectos/{id}/reapertura", response_model=ProyectoOut)
def reabrir(id: uuid.UUID, datos: ReaperturaIn, usuario: Administrador, service: ServiceDep):
    return service.reabrir(id, datos, usuario)


@router.get("/trabajadores/{id}/proyectos", response_model=list[AsignacionOut])
def asignaciones(id: uuid.UUID, usuario: LectorTrabajador, service: ServiceDep):
    return service.asignaciones_del_trabajador(id)


@router.post("/trabajadores/{id}/proyectos", status_code=201, response_model=list[AsignacionOut])
def asignar(id: uuid.UUID, datos: AsignacionIn, usuario: Asignador, service: ServiceDep):
    return service.asignar(id, datos, usuario)


@router.post("/trabajadores/{id}/proyectos/{asignacion_id}/termino", response_model=TerminoOut)
def terminar(id: uuid.UUID, asignacion_id: uuid.UUID, usuario: Asignador, service: ServiceDep):
    return service.terminar(id, asignacion_id, usuario)
