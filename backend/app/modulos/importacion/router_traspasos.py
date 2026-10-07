"""Endpoints de la importacion de traspasos (FEAT-009, TR-01 a TR-09).

Todos exigen `traspasos.operar` (por clave, nunca por el nombre del rol; NO piden
`inventario.entradas`) y respetan el alcance de almacen (AC-06). La importacion no escribe vales:
confirma por el servicio de movimientos.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status

from app.db import SesionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.importacion.lectura import MAX_BYTES_ARCHIVO
from app.modulos.importacion.schemas_traspasos import (
    ArchivoTraspasoOut,
    TraspasoConfirmarIn,
    TraspasoIn,
    TraspasoOut,
    VistaPreviaTraspasoOut,
)
from app.modulos.importacion.service_traspasos import TraspasoImportService

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter(prefix="/traspasos", tags=["importacion"])

Enviar = Annotated[Usuario, Depends(requiere_permiso(P.TRASPASOS_OPERAR))]


def get_service(session: SesionDep) -> TraspasoImportService:
    return TraspasoImportService(session)


ServiceDep = Annotated[TraspasoImportService, Depends(get_service)]


@router.get("/plantilla")
def plantilla(usuario: Enviar, service: ServiceDep) -> Response:
    """`traspasos.operar`. Descarga un `.xlsx` de ejemplo. No lee ni escribe datos."""
    return Response(
        content=service.plantilla(),
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": 'attachment; filename="plantilla-traspaso.xlsx"'},
    )


@router.post("/archivo", response_model=ArchivoTraspasoOut)
def vista_previa_de_archivo(
    usuario: Enviar,
    service: ServiceDep,
    archivo: Annotated[UploadFile, File(description="Un Excel .xlsx sin macros.")],
    destino_almacen_id: Annotated[uuid.UUID | None, Form()] = None,
    almacen_id: Annotated[uuid.UUID | None, Form()] = None,
) -> ArchivoTraspasoOut:
    """`traspasos.operar`. Lee un `.xlsx` y responde las filas separadas en columnas, las columnas
    propuestas y la vista previa. No guarda el archivo ni escribe en la base."""
    contenido = archivo.file.read(MAX_BYTES_ARCHIVO + 1)
    return service.vista_previa_de_archivo(
        usuario, archivo.filename, contenido, destino_almacen_id, almacen_id
    )


@router.post("/vista-previa", response_model=VistaPreviaTraspasoOut)
def vista_previa(datos: TraspasoIn, usuario: Enviar, service: ServiceDep) -> VistaPreviaTraspasoOut:
    """`traspasos.operar`. Evalua cada fila como la captura manual. No escribe nada."""
    return service.vista_previa(usuario, datos)


@router.post("", response_model=TraspasoOut, status_code=status.HTTP_201_CREATED)
def confirmar(
    datos: TraspasoConfirmarIn, response: Response, usuario: Enviar, service: ServiceDep
) -> TraspasoOut:
    """`traspasos.operar`. Crea UN vale de traspaso, todo o nada. Con un `id_lote` ya confirmado
    responde 200 con `repetida: true` y el mismo vale."""
    salida, creada = service.confirmar(usuario, datos)
    if not creada:
        response.status_code = status.HTTP_200_OK
    return salida
