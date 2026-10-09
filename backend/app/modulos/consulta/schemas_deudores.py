"""Filtros DU-06 compartidos por listado, tarjetas y resumen."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class DeudoresFilters(BaseModel):
    almacen_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    sin_proyecto: bool = False
    alto_valor: bool = False
    vigencia: Literal["VIGENTES", "NO_VIGENTES", "TODOS"] = "TODOS"
    antiguedad_dias: int | None = Field(default=None, ge=0, le=36500)
    q: str | None = Field(default=None, max_length=100)
