"""Identificadores: UUID versión 7 generado por el servidor (ADR-006)."""

import uuid


def nuevo_id() -> uuid.UUID:
    return uuid.uuid7()
