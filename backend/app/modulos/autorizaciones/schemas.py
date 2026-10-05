"""Contratos de entrada y salida del módulo `autorizaciones`."""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

from app.modulos.autorizaciones.models import EstadoAutorizacion, MedioAutorizacion


def _a_utc(valor: datetime) -> str:
    return valor.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# Las fechas de la base son UTC sin zona; se envían con la `Z` (api-contracts: horas en UTC).
FechaUtc = Annotated[datetime, PlainSerializer(_a_utc, return_type=str)]


class RenglonSolicitud(BaseModel):
    """Un renglón que se pide autorizar y la regla que lo originó (límite, artículo restringido)."""

    codigo: str = Field(min_length=1, max_length=60)
    articulo_id: uuid.UUID | None = None
    articulo: str | None = Field(default=None, max_length=150)
    cantidad: int = Field(ge=1)
    limite: int | None = Field(default=None, ge=0)
    tiene: int | None = Field(default=None, ge=0)
    excedente: int | None = Field(default=None, ge=0)
    regla: str = Field(min_length=1, max_length=20, description="ID de la regla, por ejemplo L-01")
    mensaje: str | None = Field(default=None, max_length=255)
    # A-06: `movimientos` marca en falso los renglones en rojo; esos no se aceptan.
    autorizable: bool = True


class SolicitudCreate(BaseModel):
    trabajador_id: uuid.UUID
    renglones: list[RenglonSolicitud] = Field(min_length=1)
    motivo: str = Field(max_length=255)
    # Solo quien opera todos los almacenes (`almacenes.todos`) lo indica; los demás usan el suyo.
    almacen_id: uuid.UUID | None = None

    @field_validator("motivo")
    @classmethod
    def _motivo_obligatorio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Escribe el motivo de la solicitud.")
        return valor


class SolicitudCreada(BaseModel):
    id: uuid.UUID
    estado: EstadoAutorizacion
    vence_en: FechaUtc


class ResolucionIn(BaseModel):
    """`{decision}` desde la sesión de quien autoriza; con `usuario` y `pin`, desde el dispositivo
    del almacenista."""

    decision: Literal["APROBAR", "RECHAZAR"]
    usuario: str | None = Field(default=None, min_length=1, max_length=60)
    pin: str | None = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def _usuario_y_pin_juntos(self) -> Self:
        if (self.usuario is None) != (self.pin is None):
            raise ValueError("Escribe el usuario y el PIN juntos.")
        return self


class PersonaOut(BaseModel):
    id: uuid.UUID
    nombre: str


class TrabajadorOut(PersonaOut):
    numero_empleado: str


class AutorizacionOut(BaseModel):
    """Estado de una solicitud (lo consulta el solicitante cada tres segundos)."""

    id: uuid.UUID
    estado: EstadoAutorizacion
    medio: MedioAutorizacion | None
    motivo: str
    trabajador_id: uuid.UUID
    almacen_id: uuid.UUID
    renglones: list[RenglonSolicitud]
    solicitada_por: PersonaOut
    resuelta_por: PersonaOut | None
    creado_en: FechaUtc
    resuelta_en: FechaUtc | None
    vence_en: FechaUtc


class SolicitudListItem(BaseModel):
    """Tarjeta del supervisor: trabajador, artículo, cuánto excede, motivo y quién la pide."""

    id: uuid.UUID
    estado: EstadoAutorizacion
    almacen_id: uuid.UUID
    trabajador: TrabajadorOut
    solicitada_por: PersonaOut
    motivo: str
    renglones: list[RenglonSolicitud]
    excedente_total: int
    creado_en: FechaUtc
    vence_en: FechaUtc


class ValidoOut(BaseModel):
    """Quién autorizó, para imprimir "Validó" en el vale (A-04)."""

    model_config = ConfigDict(from_attributes=True)

    usuario_id: uuid.UUID
    nombre: str
    medio: MedioAutorizacion
    resuelta_en: FechaUtc
    motivo: str
