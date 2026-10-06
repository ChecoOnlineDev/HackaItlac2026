"""Contraseñas, PIN y tokens de sesión.

La contraseña y el PIN son secretos distintos; ambos se guardan con Argon2.

La sesión de un dispositivo son dos cookies `HttpOnly` (AC-14 a AC-24):

- **Token de acceso** (JWT, `ACCESO_MINUTOS`, 15 por defecto): solo identifica al usuario, su
  versión de sesión y la familia (el dispositivo). Rol, permisos y almacén se leen de la base en
  cada petición.
- **Token de renovación** (opaco, hasta `REFRESH_DIAS` días): una cadena aleatoria. La base solo
  guarda su huella SHA-256 (`sesion_dispositivo.refresh_hash`); con ella se pide un token de
  acceso nuevo sin volver a escribir la contraseña.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import get_settings

_hasher = PasswordHash((Argon2Hasher(),))
ALGORITMO_JWT = "HS256"
RUTA_COOKIE_REFRESH = "/api/sesion"


def hashear_secreto(secreto: str) -> str:
    return _hasher.hash(secreto)


def verificar_secreto(secreto: str, hash_guardado: str) -> bool:
    try:
        return _hasher.verify(secreto, hash_guardado)
    except Exception:
        return False


# Hash de relleno para gastar el mismo tiempo cuando el usuario no existe.
HASH_RELLENO = hashear_secreto("relleno-sin-usuario")


def crear_token_acceso(usuario_id: uuid.UUID, version: int, familia_id: uuid.UUID) -> str:
    """Token de acceso. `version` es `usuario.version_sesion` y `familia_id` el dispositivo: si la
    versión cambia (contraseña, PIN, inactivar) o la familia se revoca, el token deja de servir."""
    ajustes = get_settings()
    ahora = datetime.now(UTC)
    carga = {
        "sub": str(usuario_id),
        "ver": version,
        "fam": str(familia_id),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=ajustes.acceso_minutos),
    }
    return jwt.encode(carga, ajustes.clave_sesion, algorithm=ALGORITMO_JWT)


@dataclass(frozen=True)
class TokenAcceso:
    usuario_id: uuid.UUID
    version: int
    familia_id: uuid.UUID


def leer_token_acceso(token: str) -> TokenAcceso | None:
    """Los datos del token de acceso, o None si es inválido, venció o no trae familia (un token
    de antes de las sesiones por dispositivo ya no sirve: hay que entrar de nuevo)."""
    try:
        carga = jwt.decode(
            token,
            get_settings().clave_sesion,
            algorithms=[ALGORITMO_JWT],
            options={"require": ["exp", "sub", "ver", "fam"]},
        )
        version = carga["ver"]
        if not isinstance(version, int) or isinstance(version, bool):
            return None
        return TokenAcceso(uuid.UUID(carga["sub"]), version, uuid.UUID(carga["fam"]))
    except jwt.PyJWTError, ValueError, KeyError:
        return None


def nuevo_token_refresh() -> str:
    """Token de renovación: 384 bits aleatorios. No es un JWT; no dice nada de quien lo trae."""
    return secrets.token_urlsafe(48)


def huella_refresh(token: str) -> str:
    """SHA-256 del token de renovación (hex). Es lo único que se guarda: el token en sí no."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _poner_cookie(response: Response, nombre: str, valor: str, segundos: int, path: str) -> None:
    response.set_cookie(
        nombre,
        valor,
        max_age=max(0, segundos),
        httponly=True,
        secure=get_settings().cookie_segura,
        samesite="lax",
        path=path,
    )


def _quitar_cookie(response: Response, nombre: str, path: str) -> None:
    response.delete_cookie(
        nombre,
        httponly=True,
        secure=get_settings().cookie_segura,
        samesite="lax",
        path=path,
    )


def poner_cookie_acceso(response: Response, token: str) -> None:
    ajustes = get_settings()
    _poner_cookie(response, ajustes.cookie_nombre, token, ajustes.acceso_minutos * 60, "/")


def poner_cookie_refresh(response: Response, token: str, segundos: int) -> None:
    """El token de renovación solo viaja a `/api/sesion` (renovar, salir, dispositivos)."""
    _poner_cookie(
        response, get_settings().cookie_refresh_nombre, token, segundos, RUTA_COOKIE_REFRESH
    )


def quitar_cookies_sesion(response: Response) -> None:
    ajustes = get_settings()
    _quitar_cookie(response, ajustes.cookie_nombre, "/")
    _quitar_cookie(response, ajustes.cookie_refresh_nombre, RUTA_COOKIE_REFRESH)
