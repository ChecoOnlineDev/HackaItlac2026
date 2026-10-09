"""Proyectos y su historial de asignaciones (PR-01 a PR-13)."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora


class Proyecto(Base):
    __tablename__ = "proyecto"
    __table_args__ = (
        UniqueConstraint("clave", name="uq_proyecto_clave"),
        CheckConstraint("fin_estimado >= inicio", name="fin_posterior_a_inicio"),
        CheckConstraint("estado IN ('ACTIVO', 'CERRADO')", name="estado"),
        Index("ix_proyecto_almacen_id_estado", "almacen_id", "estado"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    clave: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), nullable=False)
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fin_estimado: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVO")
    cerrado_en: Mapped[datetime | None] = mapped_column(FechaHora)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500))
    creado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class AsignacionProyecto(Base):
    __tablename__ = "asignacion_proyecto"
    __table_args__ = (
        UniqueConstraint(
            "trabajador_id", "proyecto_id", "activa", name="uq_asignacion_proyecto_activa"
        ),
        UniqueConstraint(
            "trabajador_id", "principal_activa", name="uq_asignacion_proyecto_principal"
        ),
        CheckConstraint(
            "fin IS NULL OR fin >= inicio OR terminada_en IS NOT NULL",
            name="fin_posterior_a_inicio",
        ),
        Index("ix_asignacion_proyecto_trabajador_id_terminada_en", "trabajador_id", "terminada_en"),
        Index("ix_asignacion_proyecto_proyecto_id_terminada_en", "proyecto_id", "terminada_en"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    trabajador_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trabajador.id"), nullable=False)
    proyecto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proyecto.id"), nullable=False)
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fin: Mapped[date | None] = mapped_column(Date)
    principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
    terminada_en: Mapped[datetime | None] = mapped_column(FechaHora)
    terminada_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    activa: Mapped[int | None] = mapped_column(
        Integer, Computed("CASE WHEN terminada_en IS NULL THEN 1 ELSE NULL END", persisted=False)
    )
    principal_activa: Mapped[int | None] = mapped_column(
        Integer,
        Computed(
            "CASE WHEN terminada_en IS NULL AND principal = 1 THEN 1 ELSE NULL END", persisted=False
        ),
    )
