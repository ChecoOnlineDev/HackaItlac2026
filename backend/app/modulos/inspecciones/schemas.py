"""Contratos de entrada y salida del módulo `inspecciones`."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, PlainSerializer, StringConstraints

from app.modulos.inspecciones.models import ResultadoInspeccion


def _a_utc(valor: datetime) -> str:
    return valor.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# Las fechas de la base son UTC sin zona; se envían con la `Z` (api-contracts: horas en UTC).
FechaUtc = Annotated[datetime, PlainSerializer(_a_utc, return_type=str)]
Observacion = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Motivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class PuntosIn(BaseModel):
    """Los puntos que se revisan (P-01). `true` es que está bien; lo omitido no se revisó."""

    model_config = ConfigDict(extra="forbid")

    etiquetas: bool | None = None
    costuras: bool | None = None
    cintas: bool | None = None
    herrajes: bool | None = None
    conectores: bool | None = None


class InspeccionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resultado: ResultadoInspeccion
    puntos: PuntosIn | None = None
    observacion: Observacion | None = None


class MarcarNoAptaIn(BaseModel):
    """P-03. Solo se puede marcar No apta; el mantenimiento y la calibración son de FEAT-004."""

    model_config = ConfigDict(extra="forbid")

    estado: Literal["NO_APTO"] = "NO_APTO"
    observacion: Observacion


class AjusteVigenciaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vigente_hasta: date
    motivo: Motivo


class PiezaEstadoOut(BaseModel):
    id: uuid.UUID
    estado: str
    inspeccion_vigente_hasta: date | None


class InspeccionOut(BaseModel):
    id: uuid.UUID
    pieza_id: uuid.UUID
    fecha: date
    resultado: ResultadoInspeccion
    puntos: dict[str, bool] | None
    observacion: str | None
    vigente_hasta: date | None
    usuario_id: uuid.UUID
    creado_en: FechaUtc
    pieza: PiezaEstadoOut


class EstadoCambiadoOut(BaseModel):
    evento_id: uuid.UUID
    estado_anterior: str
    pieza: PiezaEstadoOut


class AjusteVigenciaOut(BaseModel):
    id: uuid.UUID
    pieza_id: uuid.UUID
    inspeccion_id: uuid.UUID
    vigente_hasta_anterior: date | None
    vigente_hasta_nuevo: date
    motivo: str
    usuario_id: uuid.UUID
    creado_en: FechaUtc
    pieza: PiezaEstadoOut


class HistorialItem(BaseModel):
    """Un renglón de la línea de tiempo de la pieza; solo trae los campos de su `tipo`."""

    tipo: Literal["INSPECCION", "ESTADO", "AJUSTE_VIGENCIA"]
    id: uuid.UUID
    fecha: FechaUtc
    usuario_id: uuid.UUID
    usuario: str | None = None
    # INSPECCION
    resultado: ResultadoInspeccion | None = None
    fecha_inspeccion: date | None = None
    puntos: dict[str, bool] | None = None
    vigente_hasta: date | None = None
    # ESTADO
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    # AJUSTE_VIGENCIA
    inspeccion_id: uuid.UUID | None = None
    vigente_hasta_anterior: date | None = None
    vigente_hasta_nuevo: date | None = None
    motivo: str | None = None
    # INSPECCION y ESTADO
    observacion: str | None = None
