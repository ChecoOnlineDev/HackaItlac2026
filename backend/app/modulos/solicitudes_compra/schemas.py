"""Contratos de entrada y salida del módulo `solicitudes_compra`."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer, field_validator, model_validator

from app.modulos.solicitudes_compra.models import EstadoSolicitud, Urgencia


def _a_utc(valor: datetime) -> str:
    return valor.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# Las fechas de la base son UTC sin zona; se envían con la `Z` (api-contracts: horas en UTC).
FechaUtc = Annotated[datetime, PlainSerializer(_a_utc, return_type=str)]

# Lo que el servidor deja hacer con una solicitud a quien la consulta (SC-04, SC-07).
Accion = Literal["tomar", "rechazar", "comprar", "ingresar", "cancelar"]


def _texto(valor: str | None) -> str | None:
    """Quita espacios; un texto vacío es lo mismo que no escribir nada."""
    if valor is None:
        return None
    valor = " ".join(valor.split())
    return valor or None


# ----------------------------------------------------------------------------- entrada


class SolicitudCreate(BaseModel):
    """`POST /api/solicitudes-compra`. Un artículo del catálogo o, si no existe, su descripción."""

    # Lo genera el dispositivo para que un doble toque no duplique la solicitud (SC-10).
    id_cliente: uuid.UUID
    articulo_id: uuid.UUID | None = None
    # Obligatoria sin `articulo_id`. Con artículo se toma su nombre y este texto se ignora.
    descripcion: str | None = Field(default=None, max_length=255)
    cantidad: int = Field(ge=1, le=1_000_000)
    motivo: str = Field(max_length=255)
    urgencia: Urgencia = Urgencia.URGENTE
    # Solo quien opera todos los almacenes (`almacenes.todos`) lo indica; los demás usan el suyo.
    almacen_id: uuid.UUID | None = None

    @field_validator("descripcion")
    @classmethod
    def _limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _texto(valor)

    @field_validator("motivo")
    @classmethod
    def _motivo_obligatorio(cls, valor: str) -> str:
        limpio = _texto(valor)
        if limpio is None:
            raise ValueError("Escribe para qué trabajo o área se necesita (SC-02).")
        return limpio

    @model_validator(mode="after")
    def _articulo_o_descripcion(self) -> SolicitudCreate:
        if self.articulo_id is None and self.descripcion is None:
            raise ValueError(
                "Elige un artículo del catálogo o describe lo que se necesita (SC-02)."
            )
        return self


class CambioEstadoIn(BaseModel):
    """`POST /api/solicitudes-compra/{id}/estado`. Solo Compras (SC-04)."""

    estado: EstadoSolicitud
    # Obligatoria al rechazar (SC-05); en las demás transiciones es opcional.
    nota: str | None = Field(default=None, max_length=500)
    # Solo al pasar a INGRESADA, y es opcional (SC-06).
    vale_entrada_id: uuid.UUID | None = None

    @field_validator("nota")
    @classmethod
    def _limpiar_nota(cls, valor: str | None) -> str | None:
        return _texto(valor)


class CancelacionIn(BaseModel):
    """`POST /api/solicitudes-compra/{id}/cancelacion`."""

    nota: str | None = Field(default=None, max_length=500)

    @field_validator("nota")
    @classmethod
    def _limpiar_nota(cls, valor: str | None) -> str | None:
        return _texto(valor)


class FiltrosSolicitudes(BaseModel):
    """Filtros de `GET /api/solicitudes-compra`."""

    estado: EstadoSolicitud | None = None
    urgencia: Urgencia | None = None
    # Solo quien atiende compras o tiene `almacenes.todos`; los demás ven su almacén.
    almacen_id: uuid.UUID | None = None
    q: str | None = Field(default=None, max_length=100)
    desde: date | None = None
    hasta: date | None = None
    mias: bool = False
    solo_contar: bool = False


# ------------------------------------------------------------------------------ salida


class PersonaOut(BaseModel):
    id: uuid.UUID
    nombre: str


class AlmacenOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str


class ArticuloOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str


class ValeEntradaOut(BaseModel):
    id: uuid.UUID
    folio: str


class SolicitudOut(BaseModel):
    """Una solicitud tal como la ve quien la consulta, con lo que puede hacer con ella."""

    id: uuid.UUID
    folio: str
    estado: EstadoSolicitud
    urgencia: Urgencia
    almacen: AlmacenOut
    solicitante: PersonaOut
    # Vacío si el equipo no está en el catálogo.
    articulo: ArticuloOut | None
    descripcion: str
    cantidad: int
    motivo: str
    nota_compras: str | None
    vale_entrada: ValeEntradaOut | None
    creada_en: FechaUtc
    actualizada_en: FechaUtc
    # Calculadas por el servidor según el permiso de quien consulta y el estado actual.
    acciones: list[Accion]


class EventoOut(BaseModel):
    """Un renglón de la línea de tiempo (SC-08)."""

    id: uuid.UUID
    estado_anterior: EstadoSolicitud | None
    estado_nuevo: EstadoSolicitud
    usuario: PersonaOut
    nota: str | None
    creado_en: FechaUtc


class SolicitudDetalleOut(SolicitudOut):
    """El detalle: la solicitud y su línea de tiempo, del evento más antiguo al más reciente."""

    eventos: list[EventoOut]


class ConteoOut(BaseModel):
    """Respuesta de `solo_contar=true`: para el contador del menú."""

    total: int
