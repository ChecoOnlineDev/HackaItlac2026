"""Datos de prueba de `autorizaciones`. PENDIENTE: lo llena el agente del modulo.

Debe ser idempotente (repetible) y solo hacer `flush`; el commit lo hace
`app/datos_prueba.py`.
"""

from sqlalchemy.orm import Session


def cargar(session: Session) -> None:
    return None
