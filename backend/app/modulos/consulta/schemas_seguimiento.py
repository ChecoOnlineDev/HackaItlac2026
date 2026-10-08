"""Contratos del seguimiento de piezas (C-13): dónde está cada pieza y quién la tiene.

Nada aquí lleva costos (RG-12), CURP ni NSS (RG-13).
"""

import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, computed_field

from app.modulos.catalogo.models import EstadoPieza
from app.modulos.consulta.schemas import FechaUtc, FormatoReporte, PaginaReporte


class UbicacionSeguimiento(StrEnum):
    """Dónde está una pieza. Con `ubicacion` el listado se filtra por ALMACEN, TRABAJADOR,
    TRANSITO o BAJA; OTRA y NINGUNA solo aparecen en los elementos."""

    ALMACEN = "ALMACEN"
    TRABAJADOR = "TRABAJADOR"
    TRANSITO = "TRANSITO"
    BAJA = "BAJA"
    OTRA = "OTRA"
    NINGUNA = "NINGUNA"


class SeguimientoFilters(BaseModel):
    # Texto sobre artículo (nombre o código), serie, código de la pieza y trabajador (nombre o
    # número). Menos de dos caracteres no busca.
    q: str | None = None
    articulo_id: uuid.UUID | None = None
    # Solo se respeta dentro del alcance del usuario (AC-06).
    almacen_id: uuid.UUID | None = None
    estado: EstadoPieza | None = None
    ubicacion: UbicacionSeguimiento | None = None
    # E-29: `true` deja las piezas sin número de serie; `false`, las que ya lo tienen.
    serie_pendiente: bool | None = None
    # SG-04: `true` deja solo las piezas de alto valor y de alturas.
    alto_valor: bool | None = None
    formato: FormatoReporte = FormatoReporte.JSON


class CantidadFilters(BaseModel):
    """Filtros de la pestaña «Por cantidad» (SG-01): lo que se busca y el almacén (AC-06)."""

    q: str | None = None
    articulo_id: uuid.UUID | None = None
    almacen_id: uuid.UUID | None = None
    formato: FormatoReporte = FormatoReporte.JSON


class ArticuloSeguimientoOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    marca: str | None


class AlmacenSeguimientoOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str


class TrabajadorSeguimientoOut(BaseModel):
    id: uuid.UUID
    numero_empleado: str
    nombre: str


class DondeEstaOut(BaseModel):
    """`texto` ya viene en español llano: "En resguardo de Juan Pérez", "En Kepler", "En tránsito
    a Contratistas". En ALMACEN, `almacen` es el almacén; en TRANSITO, el almacén al que va (si
    el vale lo dice); con un trabajador, `trabajador` es quien la tiene."""

    tipo: UbicacionSeguimiento
    texto: str
    almacen: AlmacenSeguimientoOut | None = None
    trabajador: TrabajadorSeguimientoOut | None = None


class ValeSeguimientoOut(BaseModel):
    id: uuid.UUID
    folio: str


class PiezaSeguimientoItem(BaseModel):
    id: uuid.UUID
    codigo: str
    numero_serie: str | None
    articulo: ArticuloSeguimientoOut
    estado: str
    estado_texto: str
    inspeccion_vigente: bool
    inspeccion_vigente_hasta: date | None
    ubicacion: DondeEstaOut
    # Desde cuándo está ahí: el movimiento que la dejó en esa ubicación (UTC).
    desde: FechaUtc | None
    # El vale de ese movimiento; `null` si es de un almacén fuera del alcance del usuario (AC-06).
    vale: ValeSeguimientoOut | None
    # SG-04: la pieza es de una categoría de alto valor o de alturas.
    alto_valor: bool = False
    # SG-06: aviso cuando una pieza de alto valor la tiene un trabajador dado de baja o con el
    # contrato vencido.
    aviso: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def serie_pendiente(self) -> bool:
        """Derivado de `numero_serie` nulo (E-29, I-02)."""
        return not self.numero_serie


class ResumenSeguimiento(BaseModel):
    """Conteos de las piezas dentro del alcance, con el texto, el artículo y el almacén del
    filtro; no aplican `estado` ni `ubicacion` para que las tarjetas sirvan para cambiar entre
    ellos."""

    total: int
    en_almacen: int
    en_resguardo: int
    en_transito: int
    no_aptas: int
    # SG-01: cuántos artículos por cantidad hay en resguardo (otra pestaña), para que una lista de
    # piezas vacía no parezca rota. Con el texto, el artículo y el almacén del filtro.
    articulos_por_cantidad: int = 0


class PaginaSeguimiento(PaginaReporte[PiezaSeguimientoItem]):
    resumen: ResumenSeguimiento


class CantidadSeguimientoItem(BaseModel):
    """Un artículo por cantidad en resguardo de un trabajador (SG-01)."""

    trabajador: TrabajadorSeguimientoOut
    articulo: ArticuloSeguimientoOut
    unidad: str
    cantidad: int
    # Desde cuándo lo tiene: su entrega más reciente (UTC).
    desde: FechaUtc | None
    # El vale de esa entrega; `null` si es de un almacén fuera del alcance del usuario (AC-06).
    vale: ValeSeguimientoOut | None
    almacen: AlmacenSeguimientoOut | None


class ResumenCantidad(BaseModel):
    renglones: int
    unidades: int
    articulos: int
    trabajadores: int


class PaginaCantidad(PaginaReporte[CantidadSeguimientoItem]):
    resumen: ResumenCantidad
