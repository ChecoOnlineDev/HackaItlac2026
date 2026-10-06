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


class SesionDispositivo(Base):
    """Un token de renovación emitido a un dispositivo (AC-14 a AC-24).

    Cada inicio de sesión abre una `familia_id`; cada renovación crea una fila nueva de esa
    familia y deja la anterior revocada (`motivo_revocacion = 'rotada'`, `reemplazada_por`). La
    fila sin `revocada_en` es la vigente de la familia. Solo se guarda la huella del token
    (`refresh_hash`), nunca el token ni la dirección IP.
    """

    __tablename__ = "sesion_dispositivo"
    __table_args__ = (
        Index("ix_sesion_dispositivo_usuario_id", "usuario_id"),
        Index("ix_sesion_dispositivo_familia_id", "familia_id"),
        Index("ix_sesion_dispositivo_vence_absoluto", "vence_absoluto"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=nuevo_id)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )
    # Una por inicio de sesión: identifica al dispositivo a lo largo de sus renovaciones.
    familia_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    # SHA-256 (hex) del token de renovación.
    refresh_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # `usuario.version_sesion` al emitirla: si el usuario ya tiene otra, el token se rechaza.
    version_sesion: Mapped[int] = mapped_column(Integer, nullable=False)
    # Cuándo se emitió esta fila y cuándo se inició la sesión (el inicio no cambia al renovar).
    creado_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False, default=ahora_utc)
    inicio: Mapped[datetime] = mapped_column(FechaHora, nullable=False)
    ultimo_uso: Mapped[datetime] = mapped_column(FechaHora, nullable=False)
    # Ventana deslizante: cada renovación la vuelve a dar completa, sin pasar de `vence_absoluto`.
    expira_en: Mapped[datetime] = mapped_column(FechaHora, nullable=False)
    # Tope: inicio + REFRESH_TOPE_DIAS. Pasado este momento hay que entrar de nuevo.
    vence_absoluto: Mapped[datetime] = mapped_column(FechaHora, nullable=False)
    revocada_en: Mapped[datetime | None] = mapped_column(FechaHora)
    motivo_revocacion: Mapped[str | None] = mapped_column(String(30))
    # Sin llave foránea a propósito: las filas de una familia se borran juntas al purgar.
    reemplazada_por: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    # Navegador y sistema resumidos ("Chrome en Windows"); sin dirección IP.
    agente: Mapped[str | None] = mapped_column(String(120))
