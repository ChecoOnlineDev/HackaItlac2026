"""Tablas del módulo `acceso`: usuario, rol y rol_permiso. Dueño: `acceso`."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.db import Base, FechaHora


class Rol(Base):
    """Conjunto de permisos con nombre. Los roles son datos (ADR-007)."""

    __tablename__ = "rol"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    # Marca al Administrador: no se elimina ni pierde `acceso.administrar` (AC-09).
    protegido: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)


class RolPermiso(Base):
    """Permiso (clave `modulo.accion` del catálogo en código) que tiene un rol."""

    __tablename__ = "rol_permiso"

    rol_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rol.id"), primary_key=True)
    permiso: Mapped[str] = mapped_column(String(80), primary_key=True)


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        Index("ix_usuario_rol_id", "rol_id"),
        Index("ix_usuario_almacen_id", "almacen_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    usuario: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Solo quien puede autorizar tiene PIN; es un secreto distinto de la contraseña.
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    rol_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rol.id"), nullable=False)
    # Almacén asignado (uno solo). Puede ir vacío si el rol tiene `almacenes.todos` (RG-07).
    almacen_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("almacen.id"))
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)

    # Bloqueo por intentos fallidos (5 intentos -> 5 minutos)
    intentos_fallidos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(FechaHora)
    pin_intentos_fallidos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    pin_bloqueado_hasta: Mapped[datetime | None] = mapped_column(FechaHora)

    # Versión de las sesiones del usuario: el token la lleva (`ver`) y solo sirve si coincide.
    # Cerrar sesión, restablecer contraseña o PIN e inactivar al usuario la incrementan.
    version_sesion: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    rol: Mapped[Rol] = relationship(lazy="joined")
