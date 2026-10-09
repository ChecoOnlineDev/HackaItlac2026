"""AC-37: filtros de lectura para un almacén o el conjunto asignado."""

import uuid

from sqlalchemy import false

type AlcanceAlmacenes = uuid.UUID | frozenset[uuid.UUID] | None


def dentro_del_alcance(id: uuid.UUID | None, alcance: AlcanceAlmacenes) -> bool:
    if alcance is None:
        return False
    return id in alcance if isinstance(alcance, frozenset) else id == alcance


def condicion_almacenes(columna, alcance: AlcanceAlmacenes):
    if alcance is None:
        return false()
    return columna.in_(alcance) if isinstance(alcance, frozenset) else columna == alcance
