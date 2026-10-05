"""Contratos de entrada y salida del modulo `importacion`.

La tabla se lee en el navegador: al servidor llegan filas ya separadas en columnas y el mapeo
de que columna es cada dato. El costo solo viaja en las respuestas si quien importa tiene
`catalogo.costos` (RG-12); ningun vale lleva costos.
"""

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_FILAS = 5000
MAX_COLUMNAS = 30
MAX_CELDA = 500

# Datos que se pueden relacionar con una columna.
CAMPOS = (
    "codigo",
    "nombre",
    "marca",
    "categoria",
    "cantidad",
    "almacen",
    "serie",
    "costo",
    "codigo_pieza",
)


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ColumnasIn(_Estricto):
    """Indice (desde 0) de la columna de cada dato. Solo `codigo` es obligatorio.

    `codigo` es el del articulo; `codigo_pieza` es el de cada pieza en articulos por pieza.
    """

    codigo: int = Field(ge=0, lt=MAX_COLUMNAS)
    nombre: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    marca: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    categoria: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    cantidad: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    almacen: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    serie: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    costo: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    codigo_pieza: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)

    @model_validator(mode="after")
    def _sin_columnas_repetidas(self) -> ColumnasIn:
        usadas = [v for v in self.model_dump().values() if v is not None]
        if len(usadas) != len(set(usadas)):
            raise ValueError("Una columna no puede ser dos datos a la vez.")
        return self


class ImportacionIn(_Estricto):
    """Cuerpo de la vista previa y de la confirmacion.

    - `filas`: las filas de datos, sin encabezados, cada una con sus celdas.
    - `columnas`: que columna es cada dato. Sin `columnas`, se propone a partir de
      `encabezados` (nombre de cada columna).
    - `primera_fila`: numero que tiene la primera fila de `filas` en la hoja (2 si la hoja
      tenia encabezados). Los errores se reportan con ese numero.
    - `categoria_por_defecto_id` y `mapa_categorias` ({nombre en el archivo: categoria_id}):
      categoria para los articulos nuevos cuya categoria no existe.
    - `almacen_por_defecto`: clave o nombre del almacen para las filas sin almacen.
    - `id_lote`: obligatorio al confirmar; repetir la confirmacion con el mismo lote no
      duplica nada.
    """

    filas: list[list[Any]] = Field(max_length=MAX_FILAS)
    columnas: ColumnasIn | None = None
    encabezados: list[str | None] | None = Field(default=None, max_length=MAX_COLUMNAS)
    primera_fila: int = Field(default=1, ge=1, le=1_000_000)
    categoria_por_defecto_id: uuid.UUID | None = None
    mapa_categorias: dict[str, uuid.UUID] = Field(default_factory=dict, max_length=500)
    almacen_por_defecto: str | None = Field(default=None, max_length=100)
    id_lote: uuid.UUID | None = None

    @field_validator("filas")
    @classmethod
    def _celdas(cls, filas: list[list[Any]]) -> list[list[Any]]:
        for fila in filas:
            if len(fila) > MAX_COLUMNAS:
                raise ValueError(f"Una fila no puede tener más de {MAX_COLUMNAS} columnas.")
            for celda in fila:
                if celda is not None and not isinstance(celda, str | int | float):
                    raise ValueError("Cada celda es texto, número o vacía.")
                if isinstance(celda, str) and len(celda) > MAX_CELDA:
                    raise ValueError(f"Una celda no puede pasar de {MAX_CELDA} caracteres.")
        return filas

    @model_validator(mode="after")
    def _con_mapeo(self) -> ImportacionIn:
        if self.columnas is None and not self.encabezados:
            raise ValueError("Indica `columnas` o los `encabezados` para proponerlas.")
        return self


# ------------------------------------------------------------------------------- salida


class MotivoOut(BaseModel):
    """Por que no entra una fila. `regla` es el ID de la regla; `campo` la columna."""

    regla: str
    campo: str | None = None
    codigo: str
    mensaje: str


class CategoriaRefOut(BaseModel):
    id: uuid.UUID
    nombre: str


class AlmacenRefOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str


class FilaValidaOut(BaseModel):
    fila: int
    codigo: str
    nombre: str
    marca: str | None
    categoria: CategoriaRefOut | None
    control: str
    articulo_nuevo: bool
    cantidad: int
    almacen: AlmacenRefOut
    codigo_pieza: str | None
    numero_serie: str | None
    # Solo con `catalogo.costos` (RG-12); sin el permiso la clave no aparece.
    costo: Decimal | None = None
    avisos: list[str] = Field(default_factory=list)


class FilaErrorOut(BaseModel):
    """`datos` es lo que traia la fila (para descargarla y corregirla); sin costo si quien
    importa no tiene `catalogo.costos`."""

    fila: int
    datos: dict[str, str]
    motivos: list[MotivoOut]


class ArticuloNuevoOut(BaseModel):
    codigo: str
    nombre: str
    marca: str | None
    categoria: CategoriaRefOut
    control: str
    filas: int
    costo: Decimal | None = None


class CategoriaDesconocidaOut(BaseModel):
    """Una categoria del archivo que no existe: se elige una para esas filas."""

    nombre: str
    filas: list[int]


class ResumenVistaPreviaOut(BaseModel):
    total: int
    validas: int
    con_error: int
    vacias: int
    articulos_nuevos: int
    piezas: int
    unidades: int
    almacenes: int


class VistaPreviaOut(BaseModel):
    columnas: dict[str, int | None]
    avisos: list[str]
    resumen: ResumenVistaPreviaOut
    filas_validas: list[FilaValidaOut]
    filas_error: list[FilaErrorOut]
    articulos_nuevos: list[ArticuloNuevoOut]
    categorias_desconocidas: list[CategoriaDesconocidaOut]


class ArchivoOut(BaseModel):
    """Lo que devuelve subir un `.xlsx`: las filas ya separadas (para reenviarlas a la vista
    previa y a la confirmacion), los encabezados, el mapeo propuesto y la vista previa (sin
    ella si no se encontro la columna del codigo)."""

    hoja: str | None
    encabezados: list[str]
    columnas: dict[str, int | None]
    primera_fila: int
    filas: list[list[str]]
    vista_previa: VistaPreviaOut | None


class ArticuloCreadoOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    categoria: str
    control: str


class ValeImportadoOut(BaseModel):
    id: uuid.UUID
    folio: str
    almacen: AlmacenRefOut
    renglones: int
    piezas: int
    unidades: int


class ResumenImportacionOut(BaseModel):
    filas_importadas: int
    filas_con_error: int
    articulos_creados: int
    vales: int
    piezas: int
    unidades: int


class ImportacionOut(BaseModel):
    """201 al confirmar; 200 con `repetida: true` si el lote ya se habia confirmado."""

    id_lote: uuid.UUID
    repetida: bool
    resumen: ResumenImportacionOut
    articulos_creados: list[ArticuloCreadoOut]
    vales: list[ValeImportadoOut]
    # Las filas que no entraron (solo en la primera confirmacion; al repetirla va vacia).
    filas_error: list[FilaErrorOut]
    avisos: list[str]
