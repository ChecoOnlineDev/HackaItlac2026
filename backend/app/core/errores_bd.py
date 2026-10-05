"""Detecta qué restricción violó un error de PyMySQL, por su nombre estable.

OJO: MySQL reporta único (1062) y llave foránea (1452) como `IntegrityError`, pero un CHECK
violado (3819) llega como `OperationalError`. Los services deben capturar `DBAPIError` (padre de
ambos) y luego preguntar con `es_restriccion`.
"""

import re
from dataclasses import dataclass

from sqlalchemy.exc import DBAPIError

ERRNO_UNICO = 1062
ERRNO_LLAVE_FORANEA_HIJO = 1452
ERRNO_LLAVE_FORANEA_PADRE = 1451
ERRNO_CHECK = 3819

_RE_UNICO = re.compile(r"for key '(?:[^'.]+\.)?([^']+)'")
_RE_FK = re.compile(r"CONSTRAINT `([^`]+)`")
_RE_CHECK = re.compile(r"Check constraint '([^']+)'")


@dataclass(frozen=True)
class Violacion:
    errno: int | None
    restriccion: str | None


def violacion(exc: DBAPIError) -> Violacion:
    """Extrae el errno y el nombre del constraint del error original del driver."""
    orig = exc.orig
    args = getattr(orig, "args", ())
    errno = args[0] if args and isinstance(args[0], int) else None
    mensaje = str(args[1]) if len(args) > 1 else str(orig)
    nombre = None
    if errno == ERRNO_UNICO and (m := _RE_UNICO.search(mensaje)):
        nombre = m.group(1)
    elif errno in (ERRNO_LLAVE_FORANEA_HIJO, ERRNO_LLAVE_FORANEA_PADRE) and (
        m := _RE_FK.search(mensaje)
    ):
        nombre = m.group(1)
    elif errno == ERRNO_CHECK and (m := _RE_CHECK.search(mensaje)):
        nombre = m.group(1)
    return Violacion(errno, nombre)


def es_restriccion(exc: DBAPIError, nombre: str) -> bool:
    """True si el error se debe a la restricción con ese nombre (uq_*, fk_*, ck_*)."""
    return violacion(exc).restriccion == nombre
