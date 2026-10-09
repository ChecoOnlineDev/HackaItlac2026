"""CP-04: cierre por rango de días del centro de México, sin costos."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class CierreFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    desde: date
    hasta: date

    @model_validator(mode="after")
    def rango_valido(self):
        if self.desde > self.hasta:
            raise ValueError("La fecha inicial debe ser anterior o igual a la final.")
        if self.hasta == date.max:
            raise ValueError("La fecha final está fuera del rango permitido.")
        return self


class AlmacenCierreOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str
    estado: str


class TrabajadorCierreOut(BaseModel):
    id: uuid.UUID
    nombre: str
    numero_empleado: str
    cantidad: int


class ArticuloCierreOut(BaseModel):
    articulo_id: uuid.UUID
    codigo: str
    nombre: str
    unidad: str
    saldo_inicial: int
    recibido_traspasos: int
    devuelto_a_almacen: int
    otras_entradas: int
    consumido: int
    entregado_trabajadores: int
    regresado: int
    faltantes: int
    otras_salidas: int
    saldo_final: int
    devuelto_por_trabajadores: int
    cerrado_sin_devolucion: int
    en_resguardo: int
    trabajadores: list[TrabajadorCierreOut]
    diferencia: int
    cuadra: bool


class CierreOut(BaseModel):
    almacen: AlmacenCierreOut
    desde: date
    hasta: date
    articulos: list[ArticuloCierreOut]
    cuadra: bool
    atribucion_cantidades: str = "FIFO"
    reglas: list[str] = ["CP-04", "CP-05"]
