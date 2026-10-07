"""Contratos del tablero (FEAT-008, TB-01 a TB-03). Solo lectura: sin costos, CURP ni NSS."""

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.modulos.consulta.schemas import FechaUtc

LIMITE_MAXIMO_BARRAS = 20
LIMITE_POR_OMISION = 10
DIAS_MAXIMOS_RANGO = 366

NOMBRE_TODOS = "Todos los almacenes"
NOMBRE_SIN_ALMACEN = "Sin almacén asignado"


class AlcanceOut(BaseModel):
    almacen_id: uuid.UUID | None
    nombre: str
    es_todos: bool
    puede_elegir: bool


class ExistenciasTarjeta(BaseModel):
    unidades: int
    articulos: int


class ResumenTableroOut(BaseModel):
    alcance: AlcanceOut
    existencias: ExistenciasTarjeta
    resguardo_equipo_importante: int
    sin_existencia: int
    traspasos_en_transito: int
    entregas_hoy: int
    solicitudes_compra_abiertas: int
    inspecciones_por_vencer: int
    generado_en: FechaUtc


class ConsumoTableroFilters(BaseModel):
    desde: date | None = None
    hasta: date | None = None
    almacen_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    limite: int = Field(LIMITE_POR_OMISION, ge=1, le=LIMITE_MAXIMO_BARRAS)
    separar_por_almacen: bool = False


class AlmacenRefOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str


class CategoriaRefOut(BaseModel):
    id: uuid.UUID
    nombre: str


class BarraAlmacenOut(BaseModel):
    almacen_id: uuid.UUID
    almacen: str
    total: int


class BarraConsumoOut(BaseModel):
    articulo_id: uuid.UUID
    articulo: str
    categoria: CategoriaRefOut
    unidad: str
    total: int
    por_almacen: list[BarraAlmacenOut]


class OtrosOut(BaseModel):
    total: int
    articulos: int


class ConsumoTableroOut(BaseModel):
    desde: date
    hasta: date
    almacen: AlmacenRefOut | None
    categoria: CategoriaRefOut | None
    limite: int
    separar_por_almacen: bool
    barras: list[BarraConsumoOut]
    otros: OtrosOut
    total_general: int
    sin_registros: bool
