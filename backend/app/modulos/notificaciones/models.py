import uuid
from datetime import datetime

from sqlalchemy import Computed, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora


class SuscripcionPush(Base):
    __tablename__ = "suscripcion_push"
    __table_args__ = (
        UniqueConstraint("endpoint_activo", name="uq_suscripcion_push_endpoint_activo"),
        Index("ix_suscripcion_push_usuario_id_familia_id", "usuario_id", "familia_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    familia_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    endpoint: Mapped[str] = mapped_column(String(1000))
    huella_endpoint: Mapped[str] = mapped_column(String(64))
    p256dh: Mapped[str] = mapped_column(String(120))
    auth: Mapped[str] = mapped_column(String(50))
    agente: Mapped[str | None] = mapped_column(String(120))
    creada_en: Mapped[datetime] = mapped_column(FechaHora, default=ahora_utc)
    ultimo_envio: Mapped[datetime | None] = mapped_column(FechaHora)
    ultima_etiqueta: Mapped[str | None] = mapped_column(String(80))
    ultima_prueba: Mapped[datetime | None] = mapped_column(FechaHora)
    ultimo_error: Mapped[str | None] = mapped_column(String(255))
    revocada_en: Mapped[datetime | None] = mapped_column(FechaHora)
    endpoint_activo: Mapped[str | None] = mapped_column(
        String(64),
        Computed(
            "CASE WHEN revocada_en IS NULL THEN huella_endpoint ELSE NULL END", persisted=True
        ),
    )
