"""Contratos propios de la cancelación (`POST /api/vales/{id}/cancelacion`, K-02 y K-05).

La entrada (`CancelacionIn`) vive en `schemas.py`. Aquí la respuesta: el vale de cancelación, el
vale que cancela y, con `rehacer`, el `borrador` para volver a capturar el vale.
"""

import uuid

from pydantic import BaseModel, Field

from app.modulos.movimientos.models import Condicion, EstadoVale, TipoVale
from app.modulos.movimientos.schemas import ValeConfirmadoOut


class PiezaBorradorOut(BaseModel):
    """Datos de la pieza de un renglón de ENTRADA (para capturarla otra vez)."""

    codigo: str
    numero_serie: str | None


class RenglonBorradorOut(BaseModel):
    """Un renglón del borrador, con la forma de `RenglonIn` (el cuerpo de `evaluar`)."""

    codigo: str
    cantidad: int
    condicion: Condicion | None
    observacion: str | None
    # Solo en un renglón de ENTRADA de una pieza.
    pieza: PiezaBorradorOut | None = None


class BorradorOut(BaseModel):
    """Los datos del vale cancelado, listos para cargarse como borrador de un vale nuevo (K-05).

    Tiene la forma del cuerpo de `POST /api/vales/evaluar`, sin `id_cliente`, sin `firma` y sin
    `autorizacion_id`: la interfaz corrige los renglones, pide la firma que corresponda y manda
    el vale como uno nuevo, que se vuelve a evaluar completo."""

    tipo: TipoVale
    almacen_id: uuid.UUID
    trabajador_id: uuid.UUID | None
    destino_almacen_id: uuid.UUID | None
    observacion: str | None
    renglones: list[RenglonBorradorOut]


class ValeCanceladoOut(BaseModel):
    id: uuid.UUID
    folio: str
    estado: EstadoVale


class CancelacionOut(ValeConfirmadoOut):
    """201 al cancelar (200 si el `id_cliente` ya existía). `id`, `folio`, `token`, `creado_en` y
    `renglones` son los del vale de CANCELACION (sus renglones son los movimientos inversos)."""

    vale_cancelado: ValeCanceladoOut
    motivo: str
    borrador: BorradorOut | None = None
    # Interno: el router responde 201 si es nueva y 200 si es repetida. No se envía.
    creado: bool = Field(default=True, exclude=True)
