"""Contratos del tablero (FEAT-008, TB-01 a TB-03). Solo lectura: sin CURP ni NSS ni costos
de artículos. El valor agregado (FEAT-012) viaja solo en `/tablero/valor`, con
`reportes.valor_inventario`, y nunca trae el costo de un artículo."""

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
    piezas_serie_pendiente: int
    # SG-04: piezas de alto valor y de alturas en manos de trabajadores. `null` (no se envía el
    # número) si el usuario no tiene `resguardo.ver`.
    alto_valor_fuera: int | None = None
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


# ------------------------------------------------------------------ valor del inventario (VI)


class AlcanceValorOut(BaseModel):
    todos: bool
    almacen_id: uuid.UUID | None
    almacen_nombre: str | None


class ValorCategoriaOut(BaseModel):
    categoria: str
    valor: str


class ValorAlmacenOut(BaseModel):
    almacen_id: uuid.UUID
    nombre: str
    en_almacen: str
    en_resguardo: str
    total: str


class ValorInventarioOut(BaseModel):
    """Totales en pesos (texto con 2 decimales). Nunca el costo ni el valor de un artículo."""

    moneda: str = "MXN"
    alcance: AlcanceValorOut
    total: str
    en_almacen: str
    en_resguardo: str
    # `null` si el alcance es un solo almacén: el tránsito no se atribuye a un almacén.
    en_transito: str | None
    articulos_sin_costo: int
    unidades_sin_costo: int
    por_categoria: list[ValorCategoriaOut]
    por_almacen: list[ValorAlmacenOut]
    generado_en: FechaUtc
