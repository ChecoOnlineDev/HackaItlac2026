"""Tablas del módulo `inspecciones`: inspeccion, ajuste_vigencia y evento_pieza.

Las tres solo se insertan (invariante 10). El estado de la pieza lo cambia `catalogo`, que es su
dueño; este módulo le pide el cambio.
"""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum
from app.modulos.catalogo.models import EstadoPieza


class ResultadoInspeccion(StrEnum):
    APTO = "APTO"
    NO_APTO = "NO_APTO"


class Inspeccion(Base):
    __tablename__ = "inspeccion"
    __table_args__ = (
        check_enum("resultado", ResultadoInspeccion),
        Index("ix_inspeccion_pieza_id_fecha", "pieza_id", "fecha"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    pieza_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pieza.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    id_cliente: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)
    huella: Mapped[str | None] = mapped_column(String(64))
    resultado: Mapped[str] = mapped_column(String(10), nullable=False)
    # Etiquetas, costuras, cintas, herrajes y conectores: {"etiquetas": true, ...}
    puntos: Mapped[dict | None] = mapped_column(JSON)
    observacion: Mapped[str | None] = mapped_column(Text)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class AjusteVigencia(Base):
    """P-07. Al guardarse, `pieza.inspeccion_vigente_hasta` toma la fecha nueva."""

    __tablename__ = "ajuste_vigencia"
    __table_args__ = (Index("ix_ajuste_vigencia_pieza_id", "pieza_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    pieza_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pieza.id"), nullable=False)
    inspeccion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inspeccion.id"), nullable=False)
    vigente_hasta_anterior: Mapped[date | None] = mapped_column(Date)
    vigente_hasta_nuevo: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class EventoPieza(Base):
    """Cambios de estado de una pieza que no son inspección."""

    __tablename__ = "evento_pieza"
    __table_args__ = (
        check_enum("estado_anterior", EstadoPieza, "estado_anterior_valido"),
        check_enum("estado_nuevo", EstadoPieza, "estado_nuevo_valido"),
        Index("ix_evento_pieza_pieza_id_creado_en", "pieza_id", "creado_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    pieza_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pieza.id"), nullable=False)
    estado_anterior: Mapped[str] = mapped_column(String(20), nullable=False)
    estado_nuevo: Mapped[str] = mapped_column(String(20), nullable=False)
    observacion: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
