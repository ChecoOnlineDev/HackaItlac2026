"""Endpoints de `trabajadores`: lista, alta, ficha, reingreso, credencial, foto y baja.

Cada endpoint declara su permiso. Las reglas viven en `service.py`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.core.paginacion import Pagina, PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.trabajadores.schemas import (
    BajaOut,
    CodigoCreate,
    CodigoOut,
    FichaOut,
    FiltrosTrabajadores,
    FotoOut,
    PeriodoCreate,
    Situacion,
    TrabajadorCreate,
    TrabajadorListItem,
)
from app.modulos.trabajadores.service import TrabajadorService

router = APIRouter(prefix="/trabajadores", tags=["trabajadores"])


def get_service(session: SesionDep) -> TrabajadorService:
    return TrabajadorService(session)


ServiceDep = Annotated[TrabajadorService, Depends(get_service)]

UsuarioVer = Annotated[Usuario, Depends(requiere_permiso(P.TRABAJADORES_VER))]
UsuarioAdministrar = Annotated[Usuario, Depends(requiere_permiso(P.TRABAJADORES_ADMINISTRAR))]
UsuarioIniciarBaja = Annotated[Usuario, Depends(requiere_permiso(P.TRABAJADORES_INICIAR_BAJA))]

# Con `exclude_unset`, `curp` y `nss` no aparecen si el service no los asignó (RG-13).
_SIN_NO_ASIGNADOS = {"response_model_exclude_unset": True}


@router.get("", response_model=Pagina[TrabajadorListItem])
def listar(
    usuario: UsuarioVer,
    service: ServiceDep,
    pagina: PaginacionDep,
    q: str | None = None,
    situacion: Situacion | None = None,
) -> Pagina[TrabajadorListItem]:
    """`trabajadores.ver`. Lista con vigencia y situación; filtros `q` y `situacion`."""
    elementos, total = service.listar(
        FiltrosTrabajadores(q=q, situacion=situacion), limit=pagina.limit, offset=pagina.offset
    )
    return Pagina(elementos=elementos, total=total)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FichaOut, **_SIN_NO_ASIGNADOS)
def crear(datos: TrabajadorCreate, usuario: UsuarioAdministrar, service: ServiceDep) -> FichaOut:
    """`trabajadores.administrar`. Alta (T-03). 409 `TRABAJADOR_EXISTE` si ya existe (T-02)."""
    trabajador = service.crear(datos, usuario)
    return service.construir_ficha(trabajador, usuario)


@router.get("/{trabajador_id}", response_model=FichaOut, **_SIN_NO_ASIGNADOS)
def ver(trabajador_id: uuid.UUID, usuario: UsuarioVer, service: ServiceDep) -> FichaOut:
    """`trabajadores.ver`. Ficha; CURP y NSS solo con `trabajadores.ver_datos_personales`."""
    return service.ficha(trabajador_id, usuario)


@router.post(
    "/{trabajador_id}/periodos",
    status_code=status.HTTP_201_CREATED,
    response_model=FichaOut,
    **_SIN_NO_ASIGNADOS,
)
def registrar_periodo(
    trabajador_id: uuid.UUID, datos: PeriodoCreate, usuario: UsuarioAdministrar, service: ServiceDep
) -> FichaOut:
    """`trabajadores.administrar`. Reingreso o extensión (T-02): vuelve a Activo."""
    trabajador = service.registrar_periodo(trabajador_id, datos, usuario)
    return service.construir_ficha(trabajador, usuario)


@router.post("/{trabajador_id}/codigos", status_code=status.HTTP_201_CREATED)
def ligar_codigo(
    trabajador_id: uuid.UUID, datos: CodigoCreate, usuario: UsuarioAdministrar, service: ServiceDep
) -> CodigoOut:
    """`trabajadores.administrar`. Liga una credencial o genera un código propio (T-05)."""
    return service.ligar_codigo(trabajador_id, datos.codigo, usuario)


@router.post("/{trabajador_id}/foto", response_model=FotoOut)
def subir_foto(
    trabajador_id: uuid.UUID,
    archivo: Annotated[UploadFile, File(description="Imagen PNG, JPEG o WEBP")],
    usuario: UsuarioAdministrar,
    service: ServiceDep,
) -> FotoOut:
    """`trabajadores.administrar`. Sube o reemplaza la foto (T-09). Multipart, campo `archivo`."""
    # Se lee un byte de más para que el service detecte que excede el tamaño sin cargar todo.
    contenido = archivo.file.read(service.tamano_maximo_foto() + 1)
    return service.subir_foto(trabajador_id, contenido, usuario)


@router.get("/{trabajador_id}/foto")
def ver_foto(trabajador_id: uuid.UUID, usuario: UsuarioVer, service: ServiceDep) -> Response:
    """`trabajadores.ver`. Entrega la imagen con su tipo de contenido; solo con sesión."""
    mime, contenido = service.leer_foto(trabajador_id)
    return Response(
        content=contenido,
        media_type=mime,
        headers={"Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/{trabajador_id}/baja", response_model=BajaOut)
def iniciar_baja(
    trabajador_id: uuid.UUID, usuario: UsuarioIniciarBaja, service: ServiceDep
) -> BajaOut:
    """`trabajadores.iniciar_baja`. Baja en proceso (B-01) y sus pendientes (B-02)."""
    return service.iniciar_baja(trabajador_id, usuario)


@router.delete("/{trabajador_id}/baja", response_model=FichaOut, **_SIN_NO_ASIGNADOS)
def cancelar_baja(
    trabajador_id: uuid.UUID, usuario: UsuarioAdministrar, service: ServiceDep
) -> FichaOut:
    """`trabajadores.administrar`. Cancela la baja en proceso (B-07); vuelve a Activo."""
    trabajador = service.cancelar_baja(trabajador_id, usuario)
    return service.construir_ficha(trabajador, usuario)
