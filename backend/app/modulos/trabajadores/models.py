"""Tablas del módulo `trabajadores`: trabajador y periodo_contrato."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum


class EstadoTrabajador(StrEnum):
    ACTIVO = "ACTIVO"
    BAJA_EN_PROCESO = "BAJA_EN_PROCESO"
    INACTIVO = "INACTIVO"


class Trabajador(Base):
    __tablename__ = "trabajador"
    __table_args__ = (check_enum("estado", EstadoTrabajador),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    numero_empleado: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    # Datos reservados: solo con `trabajadores.ver_datos_personales` (RG-13). CURP único si existe.
    curp: Mapped[str | None] = mapped_column(String(18), unique=True)
    nss: Mapped[str | None] = mapped_column(String(11))
    tallas: Mapped[dict | None] = mapped_column(JSON)
    # Vacío si el trabajador no tiene foto (T-09). El archivo lo guarda el módulo `archivos`.
    foto_adjunto_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("adjunto.id", use_alter=True, name="fk_trabajador_foto_adjunto_id_adjunto")
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default=EstadoTrabajador.ACTIVO)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class PeriodoContrato(Base):
    """Un renglón por contrato o reingreso. El vigente es el más reciente."""

    __tablename__ = "periodo_contrato"
    __table_args__ = (
        CheckConstraint("fin >= inicio", name="fin_posterior_a_inicio"),
        Index("ix_periodo_contrato_trabajador_id_fin", "trabajador_id", "fin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    trabajador_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trabajador.id"), nullable=False)
    puesto: Mapped[str | None] = mapped_column(String(100))
    area_obra: Mapped[str | None] = mapped_column(String(100))
    referencia: Mapped[str | None] = mapped_column(String(100))
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fin: Mapped[date] = mapped_column(Date, nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
