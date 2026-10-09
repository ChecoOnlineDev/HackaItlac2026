"""Endpoints del módulo `inspecciones`: /piezas/{id}/inspecciones, /estado y /ajuste-vigencia.

Router delgado: cada endpoint declara su permiso y delega en `InspeccionService`.
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.consulta.dependencies import requiere_alguno
from app.modulos.inspecciones.schemas import (
    AjusteVigenciaIn,
    AjusteVigenciaOut,
    EstadoCambiadoOut,
    InspeccionCreate,
    InspeccionLoteIn,
    InspeccionOut,
    MarcarNoAptaIn,
)
from app.modulos.inspecciones.service import InspeccionService
from app.modulos.inspecciones.service_pendientes import PendientesService

router = APIRouter(tags=["inspecciones"])


def get_inspeccion_service(session: SesionDep) -> InspeccionService:
    return InspeccionService(session)


ServiceDep = Annotated[InspeccionService, Depends(get_inspeccion_service)]


@router.post(
    "/piezas/{pieza_id}/inspecciones",
    response_model=InspeccionOut,
    status_code=status.HTTP_201_CREATED,
)
def inspeccionar(
    pieza_id: uuid.UUID,
    datos: InspeccionCreate,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.PIEZAS_INSPECCIONAR))],
    service: ServiceDep,
    response: Response,
) -> InspeccionOut:
    """`piezas.inspeccionar`. Registra una inspección (P-01)."""
    salida = service.registrar(pieza_id, datos, usuario)
    if salida.repetida:
        response.status_code = 200
    return salida


@router.post("/piezas/{pieza_id}/estado", response_model=EstadoCambiadoOut)
def marcar_no_apta(
    pieza_id: uuid.UUID,
    datos: MarcarNoAptaIn,
    usuario: Annotated[
        Usuario, Depends(requiere_alguno(P.PIEZAS_INSPECCIONAR, P.PIEZAS_MARCAR_ESTADO))
    ],
    service: ServiceDep,
) -> EstadoCambiadoOut:
    """`piezas.inspeccionar`. Marca la pieza No apta, con observación (P-03)."""
    return service.marcar_no_apta(pieza_id, datos, usuario)


@router.post(
    "/piezas/{pieza_id}/ajuste-vigencia",
    response_model=AjusteVigenciaOut,
    status_code=status.HTTP_201_CREATED,
)
def ajustar_vigencia(
    pieza_id: uuid.UUID,
    datos: AjusteVigenciaIn,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.PIEZAS_AJUSTAR_VIGENCIA))],
    service: ServiceDep,
) -> AjusteVigenciaOut:
    """`piezas.ajustar_vigencia`. Cambia la fecha hasta la que vale la inspección (P-07)."""
    return service.ajustar_vigencia(pieza_id, datos, usuario)


@router.get("/inspecciones/pendientes")
def pendientes(
    session: SesionDep,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.INSPECCIONES_VER))],
    estado: Literal["VENCIDA", "POR_VENCER", "SIN_INSPECCION"] = "VENCIDA",
    almacen_id: uuid.UUID | None = None,
    categoria_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    ubicacion: Literal["ALMACEN", "TRABAJADOR"] | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=200)] = 50,
    solo_contar: bool = False,
):
    return PendientesService(session).consultar(
        usuario,
        {
            "estado": estado,
            "almacen_id": almacen_id,
            "categoria_id": categoria_id,
            "q": q,
            "ubicacion": ubicacion,
        },
        pagina,
        tamano,
        solo_contar,
    )


@router.post("/inspecciones/lotes")
def lote(
    datos: InspeccionLoteIn,
    service: ServiceDep,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.PIEZAS_INSPECCIONAR))],
):
    return service.registrar_lote(datos, usuario)


@router.get("/inspecciones/{inspeccion_id}/foto")
def foto(
    inspeccion_id: uuid.UUID,
    service: ServiceDep,
    usuario: Annotated[Usuario, Depends(requiere_permiso(P.INSPECCIONES_VER))],
):
    adjunto, contenido = service.foto_de_inspeccion(inspeccion_id, usuario)
    return Response(
        contenido, media_type=adjunto.mime, headers={"Cache-Control": "private, no-store"}
    )
