"""Tablas del módulo `movimientos`: vale, movimiento, existencia y serie_folio.

Solo este módulo escribe estas tablas (ADR-001). `movimiento` y `vale` solo se insertan; la única
excepción es `vale.estado` (EN_TRANSITO -> RECIBIDO, o CANCELADO). Esa regla no se puede expresar
como constraint: la hace cumplir el service.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora, check_enum


class TipoVale(StrEnum):
    ENTRADA = "ENTRADA"
    ENTREGA = "ENTREGA"
    DEVOLUCION = "DEVOLUCION"
    TRASPASO = "TRASPASO"
    RECEPCION = "RECEPCION"
    NO_ADEUDO = "NO_ADEUDO"
    CANCELACION = "CANCELACION"
    AJUSTE = "AJUSTE"


# Prefijo del folio por tipo de vale (data-model.md): CLAVE-TIPO-CONSECUTIVO.
PREFIJO_FOLIO: dict[TipoVale, str] = {
    TipoVale.ENTRADA: "ING",
    TipoVale.ENTREGA: "ENT",
    TipoVale.DEVOLUCION: "DEV",
    TipoVale.TRASPASO: "TRS",
    TipoVale.RECEPCION: "REC",
    TipoVale.NO_ADEUDO: "NAD",
    TipoVale.CANCELACION: "CAN",
    TipoVale.AJUSTE: "AJU",
}


class EstadoVale(StrEnum):
    EMITIDO = "EMITIDO"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDO = "RECIBIDO"
    RECIBIDO_CON_DIFERENCIAS = "RECIBIDO_CON_DIFERENCIAS"
    CANCELADO = "CANCELADO"


class FirmaModo(StrEnum):
    PANTALLA = "PANTALLA"
    PAPEL = "PAPEL"
    SESION = "SESION"


class Condicion(StrEnum):
    BUENO = "BUENO"
    DESGASTE = "DESGASTE"
    DANADO = "DANADO"


class Nivel(StrEnum):
    VERDE = "VERDE"
    AMARILLO = "AMARILLO"
    NARANJA = "NARANJA"
    ROJO = "ROJO"


class Vale(Base):
    __tablename__ = "vale"
    __table_args__ = (
        check_enum("tipo", TipoVale),
        check_enum("estado", EstadoVale),
        CheckConstraint(
            "firma_modo IS NULL OR firma_modo IN ('PANTALLA', 'SESION', 'PAPEL')",
            name="firma_modo_valido",
        ),
        Index("ix_vale_tipo_almacen_id_creado_en", "tipo", "almacen_id", "creado_en"),
        Index("ix_vale_trabajador_id", "trabajador_id"),
        Index("ix_vale_responsable_id_creado_en", "responsable_id", "creado_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    # Lo genera el dispositivo para que un reintento no duplique el vale.
    id_cliente: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)
    # SHA-256 del cuerpo canónico con el que se confirmó (sin la imagen ni el trazo de la firma):
    # un reintento con el mismo `id_cliente` y OTRO cuerpo se rechaza (409). Vacío en los vales
    # anteriores a esta columna y en los que no vienen de `POST /api/vales`.
    huella_cuerpo: Mapped[str | None] = mapped_column(String(64))
    hash: Mapped[str | None] = mapped_column(String(64))
    hash_anterior: Mapped[str | None] = mapped_column(String(64))
    sello_anterior_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vale.id"))
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    # CLAVE-TIPO-CONSECUTIVO, de `serie_folio`; nunca del `id` (ADR-006).
    folio: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), nullable=False)
    trabajador_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trabajador.id"))
    periodo_contrato_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("periodo_contrato.id"))
    proyecto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proyecto.id"), index=True)
    destino_almacen_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("almacen.id"))
    # Liga una recepción con su traspaso y una cancelación con el vale que cancela.
    vale_origen_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vale.id"))
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default=EstadoVale.EMITIDO)
    responsable_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    autorizacion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("autorizacion.id"))
    observacion: Mapped[str | None] = mapped_column(Text)
    firma_modo: Mapped[str | None] = mapped_column(String(10))
    firma_adjunto_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("adjunto.id", use_alter=True, name="fk_vale_firma_adjunto_id_adjunto")
    )
    # 128 bits aleatorios; abre el vale desde su QR.
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    dispositivo: Mapped[str | None] = mapped_column(String(200))
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)


class ReservaPapel(Base):
    """F-02: folio/ticket reservado para firma manuscrita antes de emitir el vale."""

    __tablename__ = "reserva_papel"
    __table_args__ = (
        UniqueConstraint("id_cliente", name="uq_reserva_papel_id_cliente"),
        UniqueConstraint("folio", name="uq_reserva_papel_folio"),
        UniqueConstraint("token", name="uq_reserva_papel_token"),
        Index("ix_reserva_papel_vence_en", "vence_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    id_cliente: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    responsable_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    folio: Mapped[str] = mapped_column(String(30), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    huella_cuerpo: Mapped[str] = mapped_column(String(64), nullable=False)
    ticket: Mapped[dict] = mapped_column(JSON, nullable=False)
    vale_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vale.id"), unique=True)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
    vence_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False)


class Movimiento(Base):
    """Renglón del vale y de la bitácora. Solo se inserta."""

    __tablename__ = "movimiento"
    __table_args__ = (
        UniqueConstraint("vale_id", "renglon"),
        check_enum("nivel", Nivel),
        CheckConstraint(
            "condicion IS NULL OR condicion IN ('BUENO', 'DESGASTE', 'DANADO')",
            name="condicion_valida",
        ),
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint("renglon > 0", name="renglon_positivo"),
        # Invariante 3: una pieza se mueve de una en una.
        CheckConstraint("pieza_id IS NULL OR cantidad = 1", name="pieza_cantidad_uno"),
        CheckConstraint("origen_id <> destino_id", name="origen_distinto_destino"),
        Index("ix_movimiento_articulo_id_creado_en", "articulo_id", "creado_en"),
        Index("ix_movimiento_origen_id", "origen_id"),
        Index("ix_movimiento_destino_id_creado_en", "destino_id", "creado_en"),
        Index(
            "ix_movimiento_trabajador_id_articulo_id_creado_en",
            "trabajador_id",
            "articulo_id",
            "creado_en",
        ),
        Index("ix_movimiento_pieza_id", "pieza_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    vale_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vale.id"), nullable=False)
    renglon: Mapped[int] = mapped_column(Integer, nullable=False)
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulo.id"), nullable=False)
    # Solo en artículos por pieza; en los de cantidad va vacío.
    pieza_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pieza.id"))
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    origen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ubicacion.id"), nullable=False)
    destino_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ubicacion.id"), nullable=False)
    # A quién se atribuye un consumo o una devolución.
    trabajador_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trabajador.id"))
    condicion: Mapped[str | None] = mapped_column(String(10))
    motivo_baja: Mapped[str | None] = mapped_column(String(255))
    nivel: Mapped[str] = mapped_column(
        String(10), nullable=False, default=Nivel.VERDE, server_default=text("'VERDE'")
    )
    # IDs de las reglas que aplicaron, por ejemplo ["E-06", "L-02"].
    reglas: Mapped[list | None] = mapped_column(JSON)
    observacion: Mapped[str | None] = mapped_column(Text)
    # Vacío en la ubicación PROVEEDOR, que no lleva existencia.
    saldo_origen: Mapped[int | None] = mapped_column(Integer)
    saldo_destino: Mapped[int | None] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class CadenaSello(Base):
    """F-06: último eslabón por almacén; el motor lo bloquea al sellar."""

    __tablename__ = "cadena_sello"

    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), primary_key=True)
    ultimo_vale_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vale.id"))
    ultimo_hash: Mapped[str | None] = mapped_column(String(64))


class Existencia(Base):
    """Suma de movimientos por ubicación y artículo. Cambia solo junto con un movimiento."""

    __tablename__ = "existencia"
    __table_args__ = (CheckConstraint("cantidad >= 0", name="cantidad_no_negativa"),)

    ubicacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ubicacion.id"), primary_key=True)
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulo.id"), primary_key=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SerieFolio(Base):
    """Contador de folios por almacén y tipo de vale (RG-06). Se bloquea al asignar folio."""

    __tablename__ = "serie_folio"
    __table_args__ = (
        check_enum("tipo", TipoVale),
        CheckConstraint("ultimo >= 0", name="ultimo_no_negativo"),
    )

    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(15), primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
