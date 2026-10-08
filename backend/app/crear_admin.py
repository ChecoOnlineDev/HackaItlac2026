"""Crea el primer administrador sin cargar datos de prueba: `python -m app.crear_admin`.

Crea el rol Administrador (todos los permisos del catálogo) y un usuario con ese rol. Es
idempotente: si el usuario ya existe, solo restablece su contraseña, su PIN y sus bloqueos.

La contraseña y el PIN se piden por la terminal (no se muestran) o, para automatizar, salen de
`ADMIN_CLAVE` y `ADMIN_PIN`. Nunca van como argumento: quedarían en el historial.
"""

import argparse
import getpass
import os
import re
import sys

from sqlalchemy.orm import Session

import app.modelos_registro  # noqa: F401
from app.db import get_sessionmaker
from app.modulos.acceso.models import Rol, Usuario
from app.modulos.acceso.permisos import CATALOGO
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.seguridad import hashear_secreto

# Mismas reglas que `UsuarioCreate` (modulos/acceso/schemas.py).
PATRON_USUARIO = re.compile(r"^[A-Za-z0-9._-]{3,60}$")
PATRON_PIN = re.compile(r"^\d{4,8}$")
CLAVE_MINIMA = 8


def _pedir(nombre: str, variable: str, *, repetir: bool) -> str:
    valor = os.environ.get(variable)
    if valor:
        return valor
    valor = getpass.getpass(f"{nombre}: ")
    if repetir and getpass.getpass(f"Repite {nombre.lower()}: ") != valor:
        sys.exit(f"{nombre} no coincide.")
    return valor


def crear_admin(session: Session, usuario: str, nombre: str, contrasena: str, pin: str) -> bool:
    """Devuelve True si creó el usuario y False si ya existía y solo lo restableció."""
    roles = RolRepository(session)
    usuarios = UsuarioRepository(session)

    rol = roles.get_by_nombre("Administrador")
    if rol is None:
        rol = roles.add(
            Rol(nombre="Administrador", descripcion="Todos los permisos.", protegido=True)
        )
    roles.reemplazar_permisos(rol.id, {p.clave for p in CATALOGO})

    existente = usuarios.get_by_usuario(usuario)
    creado = existente is None
    admin = existente or Usuario(
        usuario=usuario,
        nombre=nombre,
        contrasena_hash=hashear_secreto(contrasena),
        rol_id=rol.id,
    )
    if creado:
        usuarios.add(admin)
    admin.nombre = nombre
    admin.rol_id = rol.id
    admin.almacen_id = None
    admin.activo = True
    admin.contrasena_hash = hashear_secreto(contrasena)
    admin.pin_hash = hashear_secreto(pin)
    admin.intentos_fallidos = 0
    admin.bloqueado_hasta = None
    admin.pin_intentos_fallidos = 0
    admin.pin_bloqueado_hasta = None
    session.flush()
    return creado


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea el primer administrador.")
    parser.add_argument("--usuario", default="admin")
    parser.add_argument("--nombre", default="Administrador")
    args = parser.parse_args()

    if not PATRON_USUARIO.fullmatch(args.usuario):
        sys.exit("El usuario lleva de 3 a 60 letras, números, punto, guion o guion bajo.")
    contrasena = _pedir("Contraseña", "ADMIN_CLAVE", repetir=True)
    if len(contrasena) < CLAVE_MINIMA:
        sys.exit(f"La contraseña lleva al menos {CLAVE_MINIMA} caracteres.")
    pin = _pedir("PIN (de 4 a 8 dígitos)", "ADMIN_PIN", repetir=True)
    if not PATRON_PIN.fullmatch(pin):
        sys.exit("El PIN lleva de 4 a 8 dígitos.")
    if pin == contrasena:
        sys.exit("El PIN debe ser distinto de la contraseña.")

    with get_sessionmaker()() as session:
        try:
            creado = crear_admin(session, args.usuario, args.nombre, contrasena, pin)
            session.commit()
        except Exception:
            session.rollback()
            raise
    print(f"Administrador '{args.usuario}' {'creado' if creado else 'restablecido'}.")


if __name__ == "__main__":
    main()
