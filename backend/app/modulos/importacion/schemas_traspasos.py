"""Contratos de la importacion de traspasos (FEAT-009, TR-01 a TR-10).

Cuerpo comun de la vista previa y la confirmacion, y respuestas. Nada lleva costos (F-12).
"""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modulos.importacion.schemas import MAX_CELDA, MAX_COLUMNAS, MAX_FILAS, AlmacenRefOut
from app.modulos.movimientos.schemas import FechaUtc

# Datos que el traspaso lee de la tabla (TR-04); el resto de las columnas se ignora con aviso.
CAMPOS_TRASPASO = ("codigo", "cantidad", "codigo_pieza", "serie")


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ColumnasTraspasoIn(BaseModel):
    """Indice (desde 0) de la columna de cada dato. Acepta (y ignora con aviso) las columnas de
    otros datos, para que la interfaz pueda reenviar el mapeo que propuso `POST /archivo`."""

    model_config = ConfigDict(extra="allow")

    codigo: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    cantidad: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    codigo_pieza: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)
    serie: int | None = Field(default=None, ge=0, lt=MAX_COLUMNAS)

    def validar_sin_repetidas(self) -> None:
        usadas = [getattr(self, c) for c in CAMPOS_TRASPASO if getattr(self, c) is not None]
        if len(usadas) != len(set(usadas)):
            raise ValueError("Una columna no puede ser dos datos a la vez.")

    def ignoradas(self) -> list[str]:
        """Nombres de los datos de otras columnas que el traspaso no lee."""
        extra = self.model_extra or {}
        return sorted(k for k, v in extra.items() if v is not None)


class TraspasoIn(_Estricto):
    """Cuerpo de la vista previa. `almacen_id` (el origen) solo cuenta con `almacenes.todos`."""

    filas: list[list[Any]] = Field(max_length=MAX_FILAS)
    columnas: ColumnasTraspasoIn
    primera_fila: int = Field(default=1, ge=1, le=1_000_000)
    destino_almacen_id: uuid.UUID | None = None
    almacen_id: uuid.UUID | None = None

    @field_validator("columnas")
    @classmethod
    def _columnas_distintas(cls, columnas: ColumnasTraspasoIn) -> ColumnasTraspasoIn:
        columnas.validar_sin_repetidas()
        return columnas

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


class TraspasoConfirmarIn(TraspasoIn):
    """Lo que agrega la confirmacion."""

    id_lote: uuid.UUID | None = None
    observacion: str | None = Field(default=None, max_length=600)
    dejar_fuera_errores: bool = False
    confirmar_repetido: bool = False

    @field_validator("observacion", mode="before")
    @classmethod
    def _limpiar(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip() or None
        return valor


# ------------------------------------------------------------------------------- salida


class MotivoFilaOut(BaseModel):
    regla: str
    codigo: str
    mensaje: str


class PiezaFilaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    numero_serie: str | None


class FilaTraspasoOut(BaseModel):
    fila: int
    codigo: str
    articulo: str | None
    pieza: PiezaFilaOut | None
    cantidad: int
    disponible_en_origen: int
    nivel: str
    unida_de: list[int]
    motivos: list[MotivoFilaOut]


class RutaOut(BaseModel):
    habitual: bool
    nivel: str
    pide_observacion: bool
    mensaje: str


class ArchivoRepetidoTraspasoOut(BaseModel):
    fecha: FechaUtc


class ResumenVistaTraspasoOut(BaseModel):
    total: int
    ok: int
    avisos: int
    errores: int
    unidades: int
    piezas: int
    excedido: bool


class VistaPreviaTraspasoOut(BaseModel):
    origen: AlmacenRefOut
    destino: AlmacenRefOut
    ruta: RutaOut
    # Motivos que valen para todo el archivo y no para una fila (AL-04: almacen cerrado).
    motivos: list[MotivoFilaOut]
    puede_confirmar: bool
    archivo_repetido: ArchivoRepetidoTraspasoOut | None
    resumen: ResumenVistaTraspasoOut
    filas: list[FilaTraspasoOut]
    avisos: list[str]


class ArchivoTraspasoOut(BaseModel):
    hoja: str | None
    encabezados: list[str]
    columnas: dict[str, int | None]
    primera_fila: int
    filas: list[list[str]]
    vista_previa: VistaPreviaTraspasoOut | None


class ValeTraspasoOut(BaseModel):
    id: uuid.UUID
    folio: str
    token: str
    estado: str
    origen: AlmacenRefOut
    destino: AlmacenRefOut
    renglones: int
    piezas: int
    unidades: int


class ResumenTraspasoOut(BaseModel):
    filas_importadas: int
    filas_dejadas_fuera: int
    unidades: int
    piezas: int


class FilaDejadaFueraOut(BaseModel):
    fila: int
    motivos: list[MotivoFilaOut]


class TraspasoOut(BaseModel):
    """201 al confirmar; 200 con `repetida: true` si el lote ya se habia confirmado."""

    id_lote: uuid.UUID
    repetida: bool
    vale: ValeTraspasoOut
    resumen: ResumenTraspasoOut
    filas_dejadas_fuera: list[FilaDejadaFueraOut]
    avisos: list[str]
