"""Tabla del módulo `archivos`: adjunto. El archivo vive en el volumen, no en la base."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum


class TipoAdjunto(StrEnum):
    FIRMA = "FIRMA"
    FOTO_DANO = "FOTO_DANO"
    FOTO_TRABAJADOR = "FOTO_TRABAJADOR"
    FOTO_INSPECCION = "FOTO_INSPECCION"
    TICKET_FIRMADO = "TICKET_FIRMADO"


class Adjunto(Base):
    __tablename__ = "adjunto"
    __table_args__ = (
        check_enum("tipo", TipoAdjunto),
        CheckConstraint("tamano > 0", name="tamano_positivo"),
        Index("ix_adjunto_vale_id", "vale_id"),
        Index("ix_adjunto_movimiento_id", "movimiento_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Ruta relativa dentro del volumen, con nombre generado por el servidor.
    ruta: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    vale_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vale.id"))
    movimiento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("movimiento.id"))
    inspeccion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("inspeccion.id"), index=True)
    subido_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
