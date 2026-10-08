"""Endpoints del modulo `importacion`: plantilla, vista previa y carga desde tabla (US-IMP-001,
US-IMP-002).

Todos exigen `inventario.importar` (por clave, nunca por el nombre del rol; AC-30: importar se
separa de capturar a mano). Confirmar pide además `inventario.entradas`, porque escribe un vale
de entrada. Las respuestas usan
`response_model_exclude_unset`: sin `catalogo.costos` la clave `costo` no aparece (RG-12).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.importacion.dependencies import ImportacionServiceDep
from app.modulos.importacion.lectura import MAX_BYTES_ARCHIVO
from app.modulos.importacion.router_traspasos import router as router_traspasos
from app.modulos.importacion.schemas import (
    ArchivoOut,
    ImportacionIn,
    ImportacionOut,
    Modo,
    VistaPreviaOut,
)

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter(prefix="/importacion", tags=["importacion"])
router.include_router(router_traspasos)  # FEAT-009: /importacion/traspasos/*

Importar = Annotated[Usuario, Depends(requiere_permiso(P.INVENTARIO_IMPORTAR))]


@router.get("/plantilla")
def plantilla(
    usuario: Importar,
    service: ImportacionServiceDep,
    modo: Annotated[Modo, Query()] = "ALTA",
) -> Response:
    """`inventario.importar`. Descarga un `.xlsx` de ejemplo para ese modo; la columna de costo
    solo viene con `catalogo.costos` y solo en `ALTA`. No lee ni escribe datos."""
    nombre = "plantilla-reposicion.xlsx" if modo == "REPOSICION" else "plantilla-alta.xlsx"
    return Response(
        content=service.plantilla(usuario, modo),
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/vista-previa", response_model=VistaPreviaOut, response_model_exclude_unset=True)
def vista_previa(
    datos: ImportacionIn, usuario: Importar, service: ImportacionServiceDep
) -> VistaPreviaOut:
    """`inventario.importar`. Filas válidas, filas con error y artículos que se crearían. No
    escribe nada."""
    return service.vista_previa(usuario, datos)


@router.post("/archivo", response_model=ArchivoOut, response_model_exclude_unset=True)
def vista_previa_de_archivo(
    usuario: Importar,
    service: ImportacionServiceDep,
    archivo: Annotated[UploadFile, File(description="Un Excel .xlsx sin macros.")],
    modo: Annotated[Modo, Form()] = "ALTA",
) -> ArchivoOut:
    """`inventario.importar`. Lee un `.xlsx` y responde las filas separadas en columnas, las
    columnas propuestas y la vista previa. No guarda el archivo ni escribe en la base."""
    contenido = archivo.file.read(MAX_BYTES_ARCHIVO + 1)
    return service.vista_previa_de_archivo(usuario, archivo.filename, contenido, modo)


@router.post("", response_model=ImportacionOut, status_code=status.HTTP_201_CREATED)
def importar(
    datos: ImportacionIn,
    response: Response,
    usuario: Importar,
    service: ImportacionServiceDep,
) -> ImportacionOut:
    """`inventario.importar`. Crea los artículos que faltan y un vale de entrada por almacén,
    todo o nada. Con un `id_lote` ya confirmado responde 200 con lo guardado."""
    salida, creada = service.confirmar(usuario, datos)
    if not creada:
        response.status_code = status.HTTP_200_OK
    return salida
