"""Tabla del módulo `auditoria`: registro de cambios que no son movimientos (CF-15, AC-10)."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora


class Auditoria(Base):
    """Solo se inserta. Nunca guarda contraseñas, PIN ni hashes en `antes` o `despues`."""

    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_entidad_entidad_id_creado_en", "entidad", "entidad_id", "creado_en"),
        Index("ix_auditoria_usuario_id_creado_en", "usuario_id", "creado_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    # Vacío cuando no hay usuario identificado (por ejemplo, un intento de entrada fallido).
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad_id: Mapped[str | None] = mapped_column(String(64))
    antes: Mapped[dict | list | None] = mapped_column(JSON)
    despues: Mapped[dict | list | None] = mapped_column(JSON)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
