"""Tabla del módulo `autorizaciones`: autorizacion."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum


class EstadoAutorizacion(StrEnum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    VENCIDA = "VENCIDA"
    USADA = "USADA"


class MedioAutorizacion(StrEnum):
    PIN = "PIN"
    REMOTA = "REMOTA"


class Autorizacion(Base):
    __tablename__ = "autorizacion"
    __table_args__ = (
        check_enum("estado", EstadoAutorizacion),
        CheckConstraint("medio IS NULL OR medio IN ('PIN', 'REMOTA')", name="medio_valido"),
        # AC-07 / A-05: quien captura no se autoriza a sí mismo.
        CheckConstraint(
            "resuelta_por IS NULL OR resuelta_por <> solicitada_por", name="no_autorizarse"
        ),
        Index("ix_autorizacion_almacen_id_estado", "almacen_id", "estado"),
        Index("ix_autorizacion_solicitada_por", "solicitada_por"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), nullable=False)
    trabajador_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trabajador.id"), nullable=False)
    solicitada_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    # Renglones y regla que la originó.
    detalle: Mapped[dict | list | None] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(
        String(10), nullable=False, default=EstadoAutorizacion.PENDIENTE
    )
    resuelta_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    medio: Mapped[str | None] = mapped_column(String(10))
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
    resuelta_en: Mapped[datetime | None] = mapped_column(FechaHora)
    vence_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False)
