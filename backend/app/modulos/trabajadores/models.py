"""Tablas del módulo `trabajadores`: trabajador y periodo_contrato."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
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
    # T-10: `True` si el número se capturó a mano con `trabajadores.numero_externo`.
    numero_externo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
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


class SerieEmpleado(Base):
    """Contador del número de empleado (T-10): una sola fila, `id = 1`. Se bloquea con FOR UPDATE
    al dar de alta, en la misma transacción que guarda al trabajador."""

    __tablename__ = "serie_empleado"
    __table_args__ = (
        CheckConstraint("id = 1", name="una_sola_fila"),
        CheckConstraint("ultimo >= 0", name="ultimo_no_negativo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1, autoincrement=False)
    ultimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PeriodoContrato(Base):
    """Un renglón por contrato o reingreso. El vigente es el más reciente."""

    __tablename__ = "periodo_contrato"
    __table_args__ = (
        CheckConstraint("fin >= inicio", name="fin_posterior_a_inicio"),
        Index("ix_periodo_contrato_trabajador_id_fin", "trabajador_id", "fin"),
        Index("ix_periodo_contrato_puesto_id", "puesto_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    trabajador_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trabajador.id"), nullable=False)
    # Texto del puesto tal como se capturó; `puesto_id` lo liga al catálogo y de él sale la
    # dotación (D-01). Vacío si el nombre no coincide con ningún puesto: sin dotación.
    puesto: Mapped[str | None] = mapped_column(String(100))
    puesto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("puesto.id"))
    area_obra: Mapped[str | None] = mapped_column(String(100))
    referencia: Mapped[str | None] = mapped_column(String(100))
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fin: Mapped[date] = mapped_column(Date, nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
