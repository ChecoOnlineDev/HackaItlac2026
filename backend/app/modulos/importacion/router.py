"""Endpoints del modulo `importacion`: vista previa y carga desde tabla (US-IMP-001).

Todos exigen `inventario.entradas` (por clave, nunca por el nombre del rol). Las respuestas usan
`response_model_exclude_unset`: sin `catalogo.costos` la clave `costo` no aparece (RG-12).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.importacion.dependencies import ImportacionServiceDep
from app.modulos.importacion.lectura import MAX_BYTES_ARCHIVO
from app.modulos.importacion.schemas import (
    ArchivoOut,
    ImportacionIn,
    ImportacionOut,
    VistaPreviaOut,
)

router = APIRouter(prefix="/importacion", tags=["importacion"])

Importar = Annotated[Usuario, Depends(requiere_permiso(P.INVENTARIO_ENTRADAS))]


@router.post("/vista-previa", response_model=VistaPreviaOut, response_model_exclude_unset=True)
def vista_previa(
    datos: ImportacionIn, usuario: Importar, service: ImportacionServiceDep
) -> VistaPreviaOut:
    """`inventario.entradas`. Filas válidas, filas con error y artículos que se crearían. No
    escribe nada."""
    return service.vista_previa(usuario, datos)


@router.post("/archivo", response_model=ArchivoOut, response_model_exclude_unset=True)
def vista_previa_de_archivo(
    usuario: Importar,
    service: ImportacionServiceDep,
    archivo: Annotated[UploadFile, File(description="Un Excel .xlsx sin macros.")],
) -> ArchivoOut:
    """`inventario.entradas`. Lee un `.xlsx` y responde las filas separadas en columnas, las
    columnas propuestas y la vista previa. No guarda el archivo ni escribe en la base."""
    contenido = archivo.file.read(MAX_BYTES_ARCHIVO + 1)
    return service.vista_previa_de_archivo(usuario, archivo.filename, contenido)


@router.post("", response_model=ImportacionOut, status_code=status.HTTP_201_CREATED)
def importar(
    datos: ImportacionIn,
    response: Response,
    usuario: Importar,
    service: ImportacionServiceDep,
) -> ImportacionOut:
    """`inventario.entradas`. Crea los artículos que faltan y un vale de entrada por almacén,
    todo o nada. Con un `id_lote` ya confirmado responde 200 con lo guardado."""
    salida, creada = service.confirmar(usuario, datos)
    if not creada:
        response.status_code = status.HTTP_200_OK
    return salida
