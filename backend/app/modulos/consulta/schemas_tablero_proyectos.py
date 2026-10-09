"""TB-05 a TB-07. Totales por proyecto, sin costos unitarios ni datos personales."""

import uuid
from datetime import date

from pydantic import BaseModel

from app.modulos.consulta.schemas import FechaUtc
from app.modulos.consulta.schemas_tablero import AlcanceOut, AlmacenRefOut, CategoriaRefOut


class ProyectosTableroFilters(BaseModel):
    desde: date | None = None
    hasta: date | None = None
    almacen_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None


class TotalUsoOut(BaseModel):
    unidades: int
    valor: str | None


class UsoOut(BaseModel):
    retornables_en_resguardo: TotalUsoOut
    consumibles_consumidos: TotalUsoOut
    total: TotalUsoOut
    articulos_sin_costo: int


class UsoCategoriaOut(UsoOut):
    categoria: CategoriaRefOut | None
    nombre: str


class ProyectoUsoOut(UsoOut):
    id: uuid.UUID
    clave: str
    nombre: str
    almacen: AlmacenRefOut
    inicio: date
    fin_estimado: date
    estado: str
    situacion: str
    trabajadores_asignados: int
    por_categoria: list[UsoCategoriaOut] | None


class RangoUsoOut(BaseModel):
    desde: date
    hasta: date


class ProyectosTableroOut(BaseModel):
    alcance: AlcanceOut
    rango: RangoUsoOut
    proyectos: list[ProyectoUsoOut]
    sin_proyecto: UsoOut
    generado_en: FechaUtc
