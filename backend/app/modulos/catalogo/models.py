"""Tablas del módulo `catalogo`: categoria, articulo, pieza y codigo."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum


class TipoCategoria(StrEnum):
    EPP = "EPP"
    HERRAMIENTA = "HERRAMIENTA"


class Control(StrEnum):
    PIEZA = "PIEZA"
    CANTIDAD = "CANTIDAD"


class EstadoPieza(StrEnum):
    APTO = "APTO"
    NO_APTO = "NO_APTO"
    EN_MANTENIMIENTO = "EN_MANTENIMIENTO"
    EN_CALIBRACION = "EN_CALIBRACION"
    BAJA = "BAJA"


class TipoCodigo(StrEnum):
    TRABAJADOR = "TRABAJADOR"
    ARTICULO = "ARTICULO"
    PIEZA = "PIEZA"
    VALE = "VALE"


def _reglas_checks() -> list[CheckConstraint]:
    """Constraints comunes de los campos de regla (categoria y articulo)."""
    return [
        CheckConstraint(
            "requiere_inspeccion = 0 OR control = 'PIEZA'", name="inspeccion_solo_pieza"
        ),
        CheckConstraint(
            "vigencia_inspeccion_dias IS NULL OR vigencia_inspeccion_dias > 0",
            name="vigencia_positiva",
        ),
        CheckConstraint("limite_cantidad IS NULL OR limite_cantidad > 0", name="limite_positivo"),
        CheckConstraint(
            "limite_periodo_dias IS NULL OR limite_periodo_dias > 0", name="periodo_positivo"
        ),
        CheckConstraint("cantidad_aviso IS NULL OR cantidad_aviso > 0", name="aviso_positivo"),
    ]


class Categoria(Base):
    """Agrupa artículos; sus campos de regla son la plantilla que se copia al artículo (CF-02)."""

    __tablename__ = "categoria"
    __table_args__ = (
        check_enum("tipo", TipoCategoria),
        check_enum("control", Control),
        *_reglas_checks(),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    control: Mapped[str] = mapped_column(String(10), nullable=False)
    retornable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requiere_inspeccion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    vigencia_inspeccion_dias: Mapped[int | None] = mapped_column(Integer)
    requiere_autorizacion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    motivo_uso_especial: Mapped[str | None] = mapped_column(String(255))
    limite_cantidad: Mapped[int | None] = mapped_column(Integer)
    # Vacío significa "en posesión" (L-05).
    limite_periodo_dias: Mapped[int | None] = mapped_column(Integer)
    # Vacío significa que no hay aviso de cantidad inusual (E-27).
    cantidad_aviso: Mapped[int | None] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )


class Articulo(Base):
    """Guarda sus propias reglas; las de la categoría solo son el punto de partida."""

    __tablename__ = "articulo"
    __table_args__ = (
        check_enum("control", Control),
        *_reglas_checks(),
        CheckConstraint("costo_unitario IS NULL OR costo_unitario >= 0", name="costo_no_negativo"),
        CheckConstraint(
            "activo = 1 OR motivo_inactivacion IS NOT NULL", name="inactivo_con_motivo"
        ),
        Index("ix_articulo_categoria_id", "categoria_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    codigo: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    marca: Mapped[str | None] = mapped_column(String(80))
    modelo: Mapped[str | None] = mapped_column(String(80))
    categoria_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categoria.id"), nullable=False)
    control: Mapped[str] = mapped_column(String(10), nullable=False)
    retornable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    talla: Mapped[str | None] = mapped_column(String(20))
    unidad: Mapped[str] = mapped_column(String(20), nullable=False, default="pieza")
    # Dato reservado: solo con `catalogo.costos` (RG-12).
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    requiere_inspeccion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    vigencia_inspeccion_dias: Mapped[int | None] = mapped_column(Integer)
    requiere_autorizacion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    motivo_uso_especial: Mapped[str | None] = mapped_column(String(255))
    limite_cantidad: Mapped[int | None] = mapped_column(Integer)
    limite_periodo_dias: Mapped[int | None] = mapped_column(Integer)
    cantidad_aviso: Mapped[int | None] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    motivo_inactivacion: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class Pieza(Base):
    """Unidad física de un artículo por pieza. `ubicacion_id` la actualiza solo `movimientos`."""

    __tablename__ = "pieza"
    __table_args__ = (
        check_enum("estado", EstadoPieza),
        UniqueConstraint("articulo_id", "numero_serie"),
        Index("ix_pieza_ubicacion_id_estado", "ubicacion_id", "estado"),
        Index("ix_pieza_articulo_id", "articulo_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulo.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    numero_serie: Mapped[str | None] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default=EstadoPieza.APTO)
    inspeccion_vigente_hasta: Mapped[date | None] = mapped_column(Date)
    # Vacía solo mientras la pieza no tiene su primer movimiento (la entrada).
    ubicacion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ubicacion.id"))
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class Codigo(Base):
    """Registro único de todo lo que se escanea (RG-10). Un código identifica una sola cosa."""

    __tablename__ = "codigo"
    __table_args__ = (
        check_enum("tipo", TipoCodigo),
        Index("ix_codigo_tipo_ref_id", "tipo", "ref_id"),
    )

    codigo: Mapped[str] = mapped_column(String(64), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    # Id de la cosa identificada (trabajador, artículo, pieza o vale); según `tipo`.
    ref_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
