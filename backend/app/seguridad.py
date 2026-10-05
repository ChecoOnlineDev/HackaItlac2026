"""Contraseñas, PIN y token de sesión.

La contraseña y el PIN son secretos distintos; ambos se guardan con Argon2. El token de sesión
(JWT) solo identifica al usuario: rol, permisos y almacén se leen de la base en cada petición.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import get_settings

_hasher = PasswordHash((Argon2Hasher(),))
ALGORITMO_JWT = "HS256"


def hashear_secreto(secreto: str) -> str:
    return _hasher.hash(secreto)


def verificar_secreto(secreto: str, hash_guardado: str) -> bool:
    try:
        return _hasher.verify(secreto, hash_guardado)
    except Exception:
        return False


# Hash de relleno para gastar el mismo tiempo cuando el usuario no existe.
HASH_RELLENO = hashear_secreto("relleno-sin-usuario")


def crear_token(usuario_id: uuid.UUID, version: int = 0) -> str:
    """Token de sesión. `version` es `usuario.version_sesion`: si después cambia, el token deja
    de servir (cerrar sesión, restablecer contraseña, inactivar)."""
    ajustes = get_settings()
    ahora = datetime.now(UTC)
    carga = {
        "sub": str(usuario_id),
        "ver": version,
        "iat": ahora,
        "exp": ahora + timedelta(hours=ajustes.sesion_horas),
    }
    return jwt.encode(carga, ajustes.clave_sesion, algorithm=ALGORITMO_JWT)


def leer_token(token: str) -> tuple[uuid.UUID, int] | None:
    """Devuelve `(id del usuario, versión de sesión)` del token, o None si es inválido o venció.
    Un token sin versión (emitido antes de que existiera) cuenta como la versión 0."""
    try:
        carga = jwt.decode(
            token,
            get_settings().clave_sesion,
            algorithms=[ALGORITMO_JWT],
            options={"require": ["exp", "sub"]},
        )
        version = carga.get("ver", 0)
        if not isinstance(version, int) or isinstance(version, bool):
            return None
        return uuid.UUID(carga["sub"]), version
    except jwt.PyJWTError, ValueError, KeyError:
        return None


def poner_cookie_sesion(response: Response, token: str) -> None:
    ajustes = get_settings()
    response.set_cookie(
        ajustes.cookie_nombre,
        token,
        max_age=ajustes.sesion_horas * 3600,
        httponly=True,
        secure=ajustes.cookie_segura,
        samesite="lax",
        path="/",
    )


def quitar_cookie_sesion(response: Response) -> None:
    ajustes = get_settings()
    response.delete_cookie(
        ajustes.cookie_nombre,
        httponly=True,
        secure=ajustes.cookie_segura,
        samesite="lax",
        path="/",
    )
