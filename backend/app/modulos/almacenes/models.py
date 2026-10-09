"""Tablas del módulo `almacenes`: almacen y ubicacion."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum


class TipoAlmacen(StrEnum):
    CENTRAL = "CENTRAL"
    SUBALMACEN = "SUBALMACEN"
    PROYECTO = "PROYECTO"


class EstadoAlmacen(StrEnum):
    ACTIVO = "ACTIVO"
    CERRADO = "CERRADO"


class TipoUbicacion(StrEnum):
    ALMACEN = "ALMACEN"
    TRABAJADOR = "TRABAJADOR"
    VIRTUAL = "VIRTUAL"


class UbicacionVirtual(StrEnum):
    PROVEEDOR = "PROVEEDOR"
    EN_TRANSITO = "EN_TRANSITO"
    CONSUMIDO = "CONSUMIDO"
    BAJA = "BAJA"


class Almacen(Base):
    __tablename__ = "almacen"
    __table_args__ = (
        check_enum("tipo", TipoAlmacen),
        check_enum("estado", EstadoAlmacen),
        # AL-02: el nombre es único (la colación no distingue mayúsculas ni acentos).
        UniqueConstraint("nombre", name="uq_almacen_nombre"),
        UniqueConstraint("central_unico", name="uq_almacen_un_central"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    clave: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Arma la red: Kepler -> Contratistas -> almacenes de área.
    padre_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("almacen.id"))
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default=EstadoAlmacen.ACTIVO)
    despacho_epp_con_aprobacion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
    cerrado_en: Mapped[datetime | None] = mapped_column(FechaHora)
    # AL-02: un solo CENTRAL. Vale 1 solo si `tipo = 'CENTRAL'` y si no, NULL; el índice único
    # (MySQL no tiene índices parciales) deja pasar muchos NULL y un solo 1.
    central_unico: Mapped[int | None] = mapped_column(
        Integer,
        Computed("CASE WHEN tipo = 'CENTRAL' THEN 1 ELSE NULL END", persisted=False),
    )


class Ubicacion(Base):
    """Donde puede estar un artículo: un almacén, un trabajador o una ubicación virtual.

    Exactamente uno de `almacen_id`, `trabajador_id` y `virtual` tiene valor, y `tipo` coincide.
    """

    __tablename__ = "ubicacion"
    __table_args__ = (
        check_enum("tipo", TipoUbicacion),
        CheckConstraint(
            "`virtual` IS NULL OR `virtual` IN ('PROVEEDOR', 'EN_TRANSITO', 'CONSUMIDO', 'BAJA')",
            name="virtual_valida",
        ),
        CheckConstraint(
            "(tipo = 'ALMACEN' AND almacen_id IS NOT NULL AND trabajador_id IS NULL"
            " AND `virtual` IS NULL)"
            " OR (tipo = 'TRABAJADOR' AND trabajador_id IS NOT NULL AND almacen_id IS NULL"
            " AND `virtual` IS NULL)"
            " OR (tipo = 'VIRTUAL' AND `virtual` IS NOT NULL AND almacen_id IS NULL"
            " AND trabajador_id IS NULL)",
            name="exactamente_uno",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    almacen_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("almacen.id"), unique=True)
    trabajador_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trabajador.id"), unique=True
    )
    virtual: Mapped[str | None] = mapped_column(String(12), unique=True)
