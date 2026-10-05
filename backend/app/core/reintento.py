"""Reintento acotado ante un interbloqueo (1213) o una espera de bloqueo vencida (1205) de MySQL.

MySQL resuelve un choque entre transacciones cancelando una de ellas: no es un error del usuario
ni del servidor, y repetir la operación casi siempre funciona. `reintentar_si_interbloqueo` la
repite pocas veces y con una pausa corta; si no se logra, responde 503 `SERVICIO_NO_DISPONIBLE`
(nunca un 500).

Solo sirve para operaciones que se pueden volver a empezar desde cero: la transacción se revierte
completa antes de cada reintento, así que nada de lo hecho antes dentro de ella se conserva.
"""

import logging
import random
import time
from collections.abc import Callable

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.excepciones import ServicioOcupado

log = logging.getLogger("imhotep")

ERRNO_INTERBLOQUEO = 1213
ERRNO_ESPERA_VENCIDA = 1205
ERRNOS_REINTENTABLES = frozenset({ERRNO_INTERBLOQUEO, ERRNO_ESPERA_VENCIDA})

INTENTOS = 3
PAUSA_BASE_SEGUNDOS = 0.05


def es_interbloqueo(exc: BaseException) -> bool:
    """True si `exc` es un error de MySQL por interbloqueo o espera de bloqueo vencida."""
    if not isinstance(exc, DBAPIError):
        return False
    args = getattr(exc.orig, "args", ())
    return bool(args) and args[0] in ERRNOS_REINTENTABLES


def reintentar_si_interbloqueo[T](
    session: Session,
    operacion: Callable[[], T],
    *,
    intentos: int = INTENTOS,
    pausa: float = PAUSA_BASE_SEGUNDOS,
) -> T:
    """Ejecuta `operacion`; ante un interbloqueo revierte la sesión, espera y la repite (hasta
    `intentos` veces en total). Si todos fallan, lanza `ServicioOcupado` (503)."""
    for intento in range(1, intentos + 1):
        try:
            return operacion()
        except DBAPIError as exc:
            if not es_interbloqueo(exc):
                raise
            session.rollback()
            log.warning("Interbloqueo en la base (intento %s de %s)", intento, intentos)
            if intento == intentos:
                raise ServicioOcupado() from exc
            time.sleep(pausa * intento + random.uniform(0, pausa))
    raise AssertionError("inalcanzable")  # pragma: no cover
