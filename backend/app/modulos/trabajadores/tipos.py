"""Tipos de valor que `trabajadores` entrega a otros módulos (sin SQLAlchemy ni HTTP)."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.modulos.trabajadores.models import Trabajador


@dataclass(frozen=True)
class Vigencia:
    """Resultado de T-07. Cuando no es vigente aplica E-02 y `motivo` dice por qué."""

    vigente: bool
    motivo: str | None
    regla: str  # "T-07" si es vigente; "E-02" si no.


@dataclass(frozen=True)
class Pendiente:
    """Un retornable en resguardo del trabajador (B-02, E-17). Sin costos (RG-12)."""

    articulo_id: uuid.UUID
    articulo: str
    control: str  # PIEZA o CANTIDAD
    pieza_id: uuid.UUID | None
    codigo: str  # código de la pieza, o del artículo si es por cantidad
    numero_serie: str | None
    cantidad: int
    entregado_en: datetime | None  # UTC, del último movimiento que lo llevó al trabajador
    vale_id: uuid.UUID | None
    folio: str | None
    almacen_id: uuid.UUID | None
    almacen_clave: str | None
    almacen: str | None


@dataclass(frozen=True)
class FilaLista:
    """Un renglón de la lista: el trabajador y lo que se calcula en la consulta."""

    trabajador: Trabajador
    con_pendientes: bool
    no_adeudo_emitido: bool
