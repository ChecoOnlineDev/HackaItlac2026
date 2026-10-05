"""Servicio de auditoría: lo usan todos los módulos que cambian catálogo, accesos o permisos.

`registrar` solo hace `flush`: el registro entra en la misma transacción que el cambio que
describe, y el commit lo hace el service que lo llamó.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modulos.auditoria.models import Auditoria
from app.modulos.auditoria.repository import AuditoriaRepository

# Nunca se guardan secretos en la auditoría, aunque quien llama los incluya por descuido.
_CLAVES_SECRETAS = ("hash", "contrasena", "pin", "token", "clave")


def _limpiar(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {
            k: ("[oculto]" if any(s in str(k).lower() for s in _CLAVES_SECRETAS) else _limpiar(v))
            for k, v in valor.items()
        }
    if isinstance(valor, list | tuple):
        return [_limpiar(v) for v in valor]
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if hasattr(valor, "as_tuple"):  # Decimal
        return str(valor)
    return valor


class AuditoriaService:
    def __init__(self, session: Session) -> None:
        self.repository = AuditoriaRepository(session)

    def registrar(
        self,
        *,
        usuario_id: uuid.UUID | None,
        accion: str,
        entidad: str,
        entidad_id: uuid.UUID | str | None = None,
        antes: Any = None,
        despues: Any = None,
    ) -> Auditoria:
        """Agrega un renglón de auditoría (sin commit). `accion`, por ejemplo `sesion.entrada`."""
        return self.repository.add(
            Auditoria(
                usuario_id=usuario_id,
                accion=accion,
                entidad=entidad,
                entidad_id=None if entidad_id is None else str(entidad_id),
                antes=_limpiar(antes),
                despues=_limpiar(despues),
            )
        )


def registrar(session: Session, **datos: Any) -> Auditoria:
    """Atajo para otros módulos: `auditoria.service.registrar(session, usuario_id=..., ...)`."""
    return AuditoriaService(session).registrar(**datos)
