"""Contratos del módulo `almacenes`."""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modulos.almacenes.models import TipoAlmacen


class AlmacenResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clave: str
    nombre: str


class AlmacenHijoOut(AlmacenResumenOut):
    estado: str


class ExistenciasResumenOut(BaseModel):
    unidades: int
    articulos: int


class BloqueoCierreOut(BaseModel):
    codigo: str
    mensaje: str


class ResumenAlmacenOut(BaseModel):
    """Lo que la pantalla de administración necesita de un almacén (FEAT-008, solo con
    `almacenes.administrar`)."""

    existencias: ExistenciasResumenOut
    piezas_en_resguardo: int
    usuarios: int
    traspasos_en_transito: int
    solicitudes_compra_abiertas: int
    tiene_folios: bool
    puede_cerrar: bool
    puede_reabrir: bool
    bloqueos_cierre: list[BloqueoCierreOut]


class AlmacenOut(AlmacenResumenOut):
    """La ficha de un almacén con su lugar en la red: de quién se surte y a quién surte."""

    tipo: str
    estado: str
    padre_id: uuid.UUID | None
    padre_clave: str | None
    cerrado_en: datetime | None = None
    hijos: list[AlmacenHijoOut]
    resumen: ResumenAlmacenOut | None = None


_RE_CLAVE = re.compile(r"^[A-Z0-9]{2,10}$")


def _normalizar_clave(valor: str) -> str:
    valor = valor.strip().upper()
    if not _RE_CLAVE.fullmatch(valor):
        raise ValueError("La clave lleva de 2 a 10 letras sin acento o números.")
    return valor


def _normalizar_nombre(valor: str) -> str:
    valor = valor.strip()
    if not valor:
        raise ValueError("Escribe el nombre del almacén.")
    return valor


class AlmacenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clave: str
    nombre: str = Field(min_length=1, max_length=100)
    tipo: Literal["CENTRAL", "SUBALMACEN", "PROYECTO"]
    padre_id: uuid.UUID | None = None

    @field_validator("clave")
    @classmethod
    def _clave(cls, valor: str) -> str:
        return _normalizar_clave(valor)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, valor: str) -> str:
        return _normalizar_nombre(valor)

    def tipo_enum(self) -> TipoAlmacen:
        return TipoAlmacen(self.tipo)


class AlmacenUpdate(BaseModel):
    """Campo omitido = no cambia. `padre_id: null` explícito es un valor (solo válido en el
    central). El `tipo` no se cambia: otro campo es 422."""

    model_config = ConfigDict(extra="forbid")

    clave: str | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    padre_id: uuid.UUID | None = None

    @field_validator("clave")
    @classmethod
    def _clave(cls, valor: str | None) -> str | None:
        return None if valor is None else _normalizar_clave(valor)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, valor: str | None) -> str | None:
        return None if valor is None else _normalizar_nombre(valor)


class CambioEstadoIn(BaseModel):
    """Cuerpo opcional del cierre y la reapertura."""

    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("motivo")
    @classmethod
    def _vacio(cls, valor: str | None) -> str | None:
        return (valor or "").strip() or None


class AlmacenFilters(BaseModel):
    q: str | None = None
    categoria_id: uuid.UUID | None = None
    # `None` trae activos e inactivos; los inactivos vienen marcados (CF-11).
    activo: bool | None = None


class ExistenciaOut(BaseModel):
    articulo_id: uuid.UUID
    codigo: str
    nombre: str
    marca: str | None
    talla: str | None
    unidad: str
    control: str
    retornable: bool
    categoria_id: uuid.UUID
    categoria_nombre: str
    activo: bool
    cantidad: int
    # Lo que se puede entregar: no cuenta piezas No aptas, en mantenimiento ni en calibración.
    disponible: int


class ExistenciasOut(BaseModel):
    almacen: AlmacenResumenOut
    elementos: list[ExistenciaOut]
    total: int
