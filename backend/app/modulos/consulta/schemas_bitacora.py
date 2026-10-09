"""BT-03: filtros de lectura; no se aceptan como campos de confirmación."""

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.modulos.movimientos.models import TipoVale


class BitacoraFilters(BaseModel):
    desde: date | None = None
    hasta: date | None = None
    almacen_id: uuid.UUID | None = None
    tipo: TipoVale | None = None
    usuario_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None
    articulo_id: uuid.UUID | None = None
    lote_id: uuid.UUID | None = None
    solo_mios: bool = False
    q: str = Field(default="", max_length=100)
