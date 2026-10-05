"""Contratos de salida del módulo `almacenes`."""

import uuid

from pydantic import BaseModel, ConfigDict


class AlmacenResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clave: str
    nombre: str


class AlmacenOut(AlmacenResumenOut):
    """Un almacén con su lugar en la red: de quién se surte y a quién surte."""

    tipo: str
    estado: str
    padre_id: uuid.UUID | None
    padre_clave: str | None
    hijos: list[AlmacenResumenOut]


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
