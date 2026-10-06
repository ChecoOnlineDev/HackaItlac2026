"""Tablas del módulo `solicitudes_compra`: solicitud_compra, solicitud_compra_evento y
serie_solicitud_compra.

La solicitud no es inventario: no mueve existencias ni escribe vales. Solo guarda el pedido de
compra y su seguimiento; el vale de ENTRADA que la cumple lo hace `movimientos` y aquí solo se liga
(`vale_entrada_id`). El historial (`solicitud_compra_evento`) solo se inserta (SC-08).
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum


class EstadoSolicitud(StrEnum):
    PENDIENTE = "PENDIENTE"
    EN_COMPRA = "EN_COMPRA"
    COMPRADA = "COMPRADA"
    INGRESADA = "INGRESADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class Urgencia(StrEnum):
    URGENTE = "URGENTE"
    NORMAL = "NORMAL"


class SolicitudCompra(Base):
    __tablename__ = "solicitud_compra"
    __table_args__ = (
        check_enum("estado", EstadoSolicitud),
        check_enum("urgencia", Urgencia),
        CheckConstraint("cantidad >= 1", name="cantidad_positiva"),
        CheckConstraint("descripcion <> ''", name="descripcion_con_texto"),
        # SC-06: solo una solicitud ingresada puede estar ligada a un vale de entrada.
        CheckConstraint(
            "vale_entrada_id IS NULL OR estado = 'INGRESADA'", name="vale_solo_ingresada"
        ),
        Index("ix_solicitud_compra_almacen_id_estado", "almacen_id", "estado"),
        Index("ix_solicitud_compra_estado_urgencia_creada_en", "estado", "urgencia", "creada_en"),
        Index("ix_solicitud_compra_solicitante_id", "solicitante_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    # Lo genera el dispositivo para que un doble toque no duplique la solicitud (SC-10).
    id_cliente: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)
    # SHA-256 del cuerpo canónico con el que se creó: el mismo `id_cliente` con otro cuerpo da 409.
    huella_cuerpo: Mapped[str] = mapped_column(String(64), nullable=False)
    # CLAVE-SOL-CONSECUTIVO, del contador `serie_solicitud_compra`; nunca del `id` (SC-09).
    folio: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    # El almacén del solicitante en el momento de pedir.
    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), nullable=False)
    solicitante_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    # Vacío si el equipo no está en el catálogo (SC-02).
    articulo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articulo.id"))
    # Con artículo, es su nombre al pedir; sin él, el texto libre de quien pide.
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    # Para qué trabajo o área se necesita (SC-02).
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    urgencia: Mapped[str] = mapped_column(String(10), nullable=False, default=Urgencia.URGENTE)
    estado: Mapped[str] = mapped_column(
        String(12), nullable=False, default=EstadoSolicitud.PENDIENTE
    )
    # La última nota de Compras (rechazo, proveedor, fecha prometida...).
    nota_compras: Mapped[str | None] = mapped_column(String(500))
    # El vale de ENTRADA con el que Compras la ingresó al almacén (SC-06).
    vale_entrada_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vale.id"))
    creada_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
    actualizada_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class SolicitudCompraEvento(Base):
    """Un cambio de estado de una solicitud. Solo se inserta (SC-08)."""

    __tablename__ = "solicitud_compra_evento"
    __table_args__ = (
        Index("ix_solicitud_compra_evento_solicitud_id_creado_en", "solicitud_id", "creado_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    solicitud_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solicitud_compra.id"), nullable=False
    )
    # Vacío en el primer evento: la solicitud nace PENDIENTE.
    estado_anterior: Mapped[str | None] = mapped_column(String(12))
    estado_nuevo: Mapped[str] = mapped_column(String(12), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    nota: Mapped[str | None] = mapped_column(String(500))
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class SerieSolicitudCompra(Base):
    """Contador de folios de solicitudes por almacén solicitante (SC-09). Se bloquea al asignar."""

    __tablename__ = "serie_solicitud_compra"
    __table_args__ = (CheckConstraint("ultimo >= 0", name="ultimo_no_negativo"),)

    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
