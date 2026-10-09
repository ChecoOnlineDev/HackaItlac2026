"""Contratos de entrada y salida del módulo `autorizaciones`."""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

from app.modulos.autorizaciones.models import (
    EstadoAutorizacion,
    MedioAutorizacion,
    TipoAutorizacion,
)


def _a_utc(valor: datetime) -> str:
    return valor.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# Las fechas de la base son UTC sin zona; se envían con la `Z` (api-contracts: horas en UTC).
FechaUtc = Annotated[datetime, PlainSerializer(_a_utc, return_type=str)]


class RenglonSolicitudIn(BaseModel):
    """Lo único que el servidor toma de un renglón de la solicitud: qué y cuánto (A-02, A-06).

    Cualquier otro campo que mande el cliente (`articulo`, `limite`, `tiene`, `excedente`, `regla`,
    `mensaje`, `autorizable`...) se ignora: el servidor los arma con su propia evaluación y eso
    es lo que lee quien autoriza. Se ignoran, y no se rechazan, para no romper a las interfaces
    que aún los mandan.
    """

    codigo: str = Field(min_length=1, max_length=60)
    cantidad: int = Field(ge=1, le=1_000_000)
    observacion: str | None = Field(default=None, max_length=500)


class RenglonSolicitud(BaseModel):
    """Un renglón de una solicitud, tal como lo evaluó el servidor: la regla que lo originó
    (límite, artículo restringido) y el detalle. Es SALIDA; nunca se toma del cliente."""

    codigo: str = Field(min_length=1, max_length=60)
    renglon: int | None = Field(default=None, ge=1)
    clase: Literal["EPP", "EXCEDENTE", "CONTEXTO"] = "EXCEDENTE"
    incluye_excedente: bool = False
    observacion: str | None = Field(default=None, max_length=500)
    articulo_id: uuid.UUID | None = None
    articulo: str | None = Field(default=None, max_length=150)
    cantidad: int = Field(ge=1)
    limite: int | None = Field(default=None, ge=0)
    tiene: int | None = Field(default=None, ge=0)
    excedente: int | None = Field(default=None, ge=0)
    regla: str = Field(min_length=1, max_length=20, description="ID de la regla, por ejemplo L-01")
    mensaje: str | None = Field(default=None, max_length=255)
    # Siempre verdadero: un renglón que no es naranja no llega a guardarse (A-06).
    autorizable: bool = True


class SolicitudCreate(BaseModel):
    """EXCEDENTE (por omisión) pide `trabajador_id`; TRASLADO pide `destino_almacen_id` y no lleva
    trabajador (X-17, X-19). DESPACHO llega con FEAT-014."""

    tipo: Literal[
        TipoAutorizacion.EXCEDENTE, TipoAutorizacion.TRASLADO, TipoAutorizacion.DESPACHO
    ] = TipoAutorizacion.EXCEDENTE
    trabajador_id: uuid.UUID | None = None
    destino_almacen_id: uuid.UUID | None = None
    renglones: list[RenglonSolicitudIn] = Field(min_length=1, max_length=100)
    motivo: str | None = Field(default=None, max_length=255)
    nota: str | None = Field(default=None, max_length=255)
    id_cliente: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None
    # Solo quien opera todos los almacenes (`almacenes.todos`) lo indica; los demás usan el suyo.
    almacen_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _campos_segun_tipo(self) -> Self:
        if self.tipo == TipoAutorizacion.TRASLADO:
            if self.trabajador_id is not None:
                raise ValueError("Un traslado no lleva trabajador.")
            if self.destino_almacen_id is None:
                raise ValueError("Elige a qué almacén se envía.")
        else:
            if self.trabajador_id is None:
                raise ValueError("Elige al trabajador.")
            if self.destino_almacen_id is not None:
                raise ValueError("El destino es solo de un traslado.")
        return self

    @field_validator("motivo", "nota")
    @classmethod
    def _limpiar_texto(cls, valor: str | None) -> str | None:
        return valor.strip() or None if valor else None


class SolicitudCreada(BaseModel):
    id: uuid.UUID
    tipo: TipoAutorizacion = TipoAutorizacion.EXCEDENTE
    estado: EstadoAutorizacion
    vence_en: FechaUtc
    avisados: int = 0


class ResolucionRenglonIn(BaseModel):
    renglon: int = Field(ge=1, le=100)
    decision: Literal["APROBAR", "RECHAZAR"]
    motivo: str | None = Field(default=None, max_length=500)


class ResolucionIn(BaseModel):
    """`{decision}` desde la sesión de quien autoriza; con `usuario` y `pin`, desde el dispositivo
    del almacenista."""

    decision: Literal["APROBAR", "RECHAZAR"] | None = None
    motivo: str | None = Field(default=None, max_length=500)
    usuario: str | None = Field(default=None, min_length=1, max_length=60)
    pin: str | None = Field(default=None, min_length=1, max_length=50)
    # DE-06: DESPACHO y EXCEDENTE admiten resolución parcial; TRASLADO sigue entero (X-19).
    renglones: list[ResolucionRenglonIn] | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def _usuario_y_pin_juntos(self) -> Self:
        if (self.decision is None) == (self.renglones is None):
            raise ValueError("Elige aprobar o rechazar todo, o decide por renglón.")
        if (self.usuario is None) != (self.pin is None):
            raise ValueError("Escribe el usuario y el PIN juntos.")
        return self


class PersonaOut(BaseModel):
    id: uuid.UUID
    nombre: str


class TrabajadorOut(PersonaOut):
    numero_empleado: str
    tiene_foto: bool = False


class AlmacenRefOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str


class AutorizacionOut(BaseModel):
    """Estado de una solicitud (lo consulta el solicitante cada tres segundos)."""

    nota: str | None = None
    proyecto: dict | None = None
    almacen: AlmacenRefOut | None = None
    incluye_excedente: bool = False
    renglones_resueltos: list[dict] | None = None
    servidor_ahora: FechaUtc
    avisados: int = 0
    id: uuid.UUID
    tipo: TipoAutorizacion = TipoAutorizacion.EXCEDENTE
    estado: EstadoAutorizacion
    medio: MedioAutorizacion | None
    motivo: str
    # Nulos en un TRASLADO.
    trabajador_id: uuid.UUID | None
    trabajador: TrabajadorOut | None = None
    # `almacen_id` es el almacén de la solicitud (en un TRASLADO, el origen).
    almacen_id: uuid.UUID
    # Solo en un TRASLADO.
    origen: AlmacenRefOut | None = None
    destino: AlmacenRefOut | None = None
    renglones: list[RenglonSolicitud]
    solicitada_por: PersonaOut
    resuelta_por: PersonaOut | None
    creado_en: FechaUtc
    resuelta_en: FechaUtc | None
    vence_en: FechaUtc


class SolicitudListItem(BaseModel):
    """Tarjeta del supervisor: trabajador (o origen y destino), artículo, cuánto excede, motivo y
    quién la pide."""

    nota: str | None = None
    proyecto: dict | None = None
    almacen: AlmacenRefOut | None = None
    incluye_excedente: bool = False
    renglones_resueltos: list[dict] | None = None
    servidor_ahora: FechaUtc
    avisados: int = 0
    id: uuid.UUID
    tipo: TipoAutorizacion = TipoAutorizacion.EXCEDENTE
    estado: EstadoAutorizacion
    almacen_id: uuid.UUID
    # Nulo en un TRASLADO.
    trabajador: TrabajadorOut | None
    origen: AlmacenRefOut | None = None
    destino: AlmacenRefOut | None = None
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


class ResolucionMultipleItem(BaseModel):
    id: uuid.UUID
    decision: Literal["APROBAR", "RECHAZAR"]
    motivo: str | None = Field(default=None, max_length=500)


class ResolucionMultipleIn(BaseModel):
    resoluciones: list[ResolucionMultipleItem] = Field(min_length=1, max_length=50)


class ResultadoResolucion(BaseModel):
    id: uuid.UUID
    estado: EstadoAutorizacion | None = None
    error: dict | None = None


class ResolucionMultipleOut(BaseModel):
    resultados: list[ResultadoResolucion]
