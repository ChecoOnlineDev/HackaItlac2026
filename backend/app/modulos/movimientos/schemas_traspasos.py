"""Contratos de `GET /api/traspasos/por-recibir` (traspasos en camino hacia un almacén).

Sin costos (RG-12). Es el único contrato propio de TRASPASO y RECEPCION: sus cuerpos de
`evaluar` y `confirmar` son los comunes del módulo (`ValeIn`).
"""

import uuid

from pydantic import BaseModel

from app.modulos.movimientos.models import EstadoVale
from app.modulos.movimientos.schemas import AlmacenResumenOut, FechaUtc, PersonaOut


class RenglonPorRecibirOut(BaseModel):
    """Un renglón del traspaso. `codigo` es lo que hay que escanear al recibirlo: el de la pieza,
    o el del artículo si es por cantidad."""

    renglon: int
    articulo_id: uuid.UUID
    articulo: str
    marca: str | None
    modelo: str | None
    talla: str | None
    codigo: str
    pieza_id: uuid.UUID | None
    numero_serie: str | None
    cantidad_enviada: int
    cantidad_recibida: int
    cantidad_pendiente: int


class RecepcionResumenOut(BaseModel):
    id: uuid.UUID
    folio: str
    creado_en: FechaUtc
    recibio: PersonaOut


class TraspasoPorRecibirOut(BaseModel):
    id: uuid.UUID
    folio: str
    token: str
    estado: EstadoVale
    origen: AlmacenResumenOut
    destino: AlmacenResumenOut
    envio: PersonaOut
    creado_en: FechaUtc
    # Lo que todavía no llega, en piezas y unidades.
    pendiente_total: int
    renglones: list[RenglonPorRecibirOut]
    recepciones: list[RecepcionResumenOut]


class PorRecibirOut(BaseModel):
    total: int
    elementos: list[TraspasoPorRecibirOut]


class TotalPorRecibirOut(BaseModel):
    """Con `?solo_contar=true`: solo cuántos traspasos vienen en camino (contador del inicio)."""

    total: int
