"""Contratos de entrada y salida del módulo `catalogo`.

`costo_unitario` es un dato reservado (RG-12): las salidas lo declaran, pero el service no lo
asigna a quien no tiene `catalogo.costos`, y los endpoints usan `response_model_exclude_unset`,
así que la clave ni siquiera aparece en la respuesta.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.modulos.catalogo.models import Control, TipoCategoria

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Costo = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=2),
    AfterValidator(lambda v: v.quantize(Decimal("0.01"))),
]

# Campos de regla compartidos por la plantilla de la categoría y el artículo (CF-02).
CAMPOS_REGLA = (
    "requiere_inspeccion",
    "vigencia_inspeccion_dias",
    "requiere_autorizacion",
    "motivo_uso_especial",
    "limite_cantidad",
    "limite_periodo_dias",
    "cantidad_aviso",
)


def _sin_nulos(modelo: BaseModel, campos: tuple[str, ...]) -> None:
    """En un PATCH, un campo obligatorio puede omitirse pero no mandarse en `null`."""
    nulos = [c for c in campos if c in modelo.model_fields_set and getattr(modelo, c) is None]
    if nulos:
        raise ValueError(f"No puede quedar vacío: {', '.join(nulos)}.")


# ---------------------------------------------------------------------------- categoría


class _ReglasBase(BaseModel):
    requiere_inspeccion: bool = False
    vigencia_inspeccion_dias: int | None = Field(default=None, gt=0)
    requiere_autorizacion: bool = False
    motivo_uso_especial: str | None = Field(default=None, max_length=255)
    limite_cantidad: int | None = Field(default=None, gt=0)
    # Vacío significa "en posesión" (L-05).
    limite_periodo_dias: int | None = Field(default=None, gt=0)
    # Vacío significa que no hay aviso de cantidad inusual (E-27).
    cantidad_aviso: int | None = Field(default=None, gt=0)


class CategoriaCreate(_ReglasBase):
    model_config = ConfigDict(extra="forbid")

    nombre: Texto = Field(max_length=100)
    tipo: TipoCategoria
    control: Control
    retornable: bool


class CategoriaUpdate(BaseModel):
    """Todos los campos son opcionales: se cambia solo lo que viene (omitido no es `null`)."""

    model_config = ConfigDict(extra="forbid")

    nombre: Texto | None = Field(default=None, max_length=100)
    tipo: TipoCategoria | None = None
    control: Control | None = None
    retornable: bool | None = None
    requiere_inspeccion: bool | None = None
    vigencia_inspeccion_dias: int | None = Field(default=None, gt=0)
    requiere_autorizacion: bool | None = None
    motivo_uso_especial: str | None = Field(default=None, max_length=255)
    limite_cantidad: int | None = Field(default=None, gt=0)
    limite_periodo_dias: int | None = Field(default=None, gt=0)
    cantidad_aviso: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _obligatorios(self) -> CategoriaUpdate:
        _sin_nulos(
            self,
            (
                "nombre",
                "tipo",
                "control",
                "retornable",
                "requiere_inspeccion",
                "requiere_autorizacion",
            ),
        )
        return self


class CategoriaOut(_ReglasBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    tipo: str
    control: str
    retornable: bool
    activo: bool


class CategoriaFilters(BaseModel):
    activo: bool | None = None


# ---------------------------------------------------------------------------- artículo


class ArticuloCreate(BaseModel):
    """Crea un artículo. Lo que no se indica (control, retorno y reglas) lo toma de su categoría.

    Un campo de regla enviado en `null` significa "sin esa regla", no "usa la plantilla".
    """

    model_config = ConfigDict(extra="forbid")

    codigo: Texto = Field(max_length=64)
    nombre: Texto = Field(max_length=150)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    categoria_id: uuid.UUID
    control: Control | None = None
    retornable: bool | None = None
    talla: str | None = Field(default=None, max_length=20)
    unidad: Texto = Field(default="pieza", max_length=20)
    # Solo se acepta con `catalogo.costos` (RG-12).
    costo_unitario: Costo | None = None
    requiere_inspeccion: bool | None = None
    vigencia_inspeccion_dias: int | None = Field(default=None, gt=0)
    requiere_autorizacion: bool | None = None
    motivo_uso_especial: str | None = Field(default=None, max_length=255)
    limite_cantidad: int | None = Field(default=None, gt=0)
    limite_periodo_dias: int | None = Field(default=None, gt=0)
    cantidad_aviso: int | None = Field(default=None, gt=0)


class ArticuloUpdate(BaseModel):
    """Edita datos, requisitos y límites. El código no cambia; la inactivación tiene su ruta."""

    model_config = ConfigDict(extra="forbid")

    nombre: Texto | None = Field(default=None, max_length=150)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    categoria_id: uuid.UUID | None = None
    control: Control | None = None
    retornable: bool | None = None
    talla: str | None = Field(default=None, max_length=20)
    unidad: Texto | None = Field(default=None, max_length=20)
    costo_unitario: Costo | None = None
    requiere_inspeccion: bool | None = None
    vigencia_inspeccion_dias: int | None = Field(default=None, gt=0)
    requiere_autorizacion: bool | None = None
    motivo_uso_especial: str | None = Field(default=None, max_length=255)
    limite_cantidad: int | None = Field(default=None, gt=0)
    limite_periodo_dias: int | None = Field(default=None, gt=0)
    cantidad_aviso: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _obligatorios(self) -> ArticuloUpdate:
        _sin_nulos(
            self,
            (
                "nombre",
                "categoria_id",
                "control",
                "retornable",
                "unidad",
                "requiere_inspeccion",
                "requiere_autorizacion",
            ),
        )
        return self


class InactivacionIn(BaseModel):
    motivo: Texto = Field(max_length=255)


class ArticuloListItem(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    marca: str | None
    modelo: str | None
    categoria_id: uuid.UUID
    categoria_nombre: str
    control: str
    retornable: bool
    talla: str | None
    unidad: str
    requiere_inspeccion: bool
    requiere_autorizacion: bool
    activo: bool
    motivo_inactivacion: str | None = None
    # Dato reservado: ausente sin `catalogo.costos`.
    costo_unitario: Decimal | None = None


class ArticuloOut(ArticuloListItem):
    vigencia_inspeccion_dias: int | None
    motivo_uso_especial: str | None
    limite_cantidad: int | None
    limite_periodo_dias: int | None
    cantidad_aviso: int | None
    creado_en: datetime


class ExistenciaAlmacenOut(BaseModel):
    almacen_id: uuid.UUID
    clave: str
    nombre: str
    cantidad: int
    # No cuenta piezas No aptas, en mantenimiento, en calibración ni de baja.
    disponible: int


class PoseedorOut(BaseModel):
    trabajador_id: uuid.UUID
    numero_empleado: str
    nombre: str
    cantidad: int


class ArticuloFichaOut(ArticuloOut):
    """Ficha del artículo (C-03): sus reglas, dónde hay y quién lo tiene."""

    # Verdadero con movimientos: control y retorno quedan bloqueados (CF-05).
    tiene_movimientos: bool
    existencias: list[ExistenciaAlmacenOut]
    en_posesion: list[PoseedorOut]


class ArticuloFilters(BaseModel):
    q: str | None = None
    categoria_id: uuid.UUID | None = None
    # `None` trae todos; la pantalla de catálogo manda `true` por defecto (CF-10).
    activo: bool | None = None


# ----------------------------------------------------------------------------- etiquetas


class TipoEtiqueta(StrEnum):
    CREDENCIALES = "credenciales"
    PIEZAS = "piezas"
    ESTANTES = "estantes"


class EtiquetaOut(BaseModel):
    """Una etiqueta: el QR contiene exactamente `codigo`; `texto` es lo legible.

    En credenciales trae además `nombre`, `numero_empleado` y `puesto` (este último solo si el
    trabajador lo tiene) para armar la tarjeta; en piezas y estantes esos campos no salen.
    """

    codigo: str
    texto: str
    nombre: str | None = None
    numero_empleado: str | None = None
    puesto: str | None = None


class EtiquetasOut(BaseModel):
    elementos: list[EtiquetaOut]
    total: int


# ------------------------------------------------------------------------------- puestos


class PuestoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Texto = Field(max_length=100)


class PuestoUpdate(BaseModel):
    """Se cambia solo lo que viene (omitido no es `null`)."""

    model_config = ConfigDict(extra="forbid")

    nombre: Texto | None = Field(default=None, max_length=100)
    activo: bool | None = None

    @model_validator(mode="after")
    def _obligatorios(self) -> PuestoUpdate:
        _sin_nulos(self, ("nombre", "activo"))
        return self


class PuestoFilters(BaseModel):
    activo: bool | None = None


class PuestoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    activo: bool
    # Artículos distintos en su dotación (D-01).
    total_articulos: int


class PuestoRefOut(BaseModel):
    id: uuid.UUID
    nombre: str


class ArticuloDotacionOut(BaseModel):
    """Lo mínimo de un artículo para listar una dotación. Sin costo (RG-12)."""

    id: uuid.UUID
    codigo: str
    nombre: str
    unidad: str
    control: str


class LimiteOut(BaseModel):
    """El límite del artículo (4.1): `periodo_dias` vacío significa "en posesión" (L-05)."""

    cantidad: int
    periodo_dias: int | None


class RenglonDotacionOut(BaseModel):
    articulo: ArticuloDotacionOut
    cantidad: int
    # `None` si el artículo no tiene límite (L-01).
    limite: LimiteOut | None


class DotacionOut(BaseModel):
    puesto: PuestoRefOut
    renglones: list[RenglonDotacionOut]


class RenglonDotacionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    articulo_id: uuid.UUID
    cantidad: int = Field(ge=1, le=1000)


class DotacionIn(BaseModel):
    """Reemplaza toda la dotación del puesto: lo que no viene se quita. Vacía la deja sin
    dotación."""

    model_config = ConfigDict(extra="forbid")

    renglones: list[RenglonDotacionIn] = Field(max_length=200)


class SerieIn(BaseModel):
    """P-08: el número de serie que se pone a una pieza que no lo tenía."""

    model_config = ConfigDict(extra="forbid")

    numero_serie: Texto = Field(max_length=80)
