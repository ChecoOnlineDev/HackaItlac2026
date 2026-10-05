"""Carga repetible de datos de prueba: `uv run python -m app.datos_prueba`.

Orquesta una función `cargar(session)` por módulo. Cada una es idempotente (se puede correr varias
veces) y solo hace `flush`; el commit lo hace este script, una sola vez, al final.

Para agregar datos de un módulo, llena su `modulos/<modulo>/datos_prueba.py`; ya está en el orden.
"""

import logging

from sqlalchemy.orm import Session

import app.modelos_registro  # noqa: F401
from app import datos_prueba_piezas as piezas
from app.db import get_sessionmaker
from app.modulos.acceso import datos_prueba as acceso
from app.modulos.almacenes import datos_prueba as almacenes
from app.modulos.autorizaciones import datos_prueba as autorizaciones
from app.modulos.catalogo import datos_prueba as catalogo
from app.modulos.inspecciones import datos_prueba as inspecciones
from app.modulos.movimientos import datos_prueba as movimientos
from app.modulos.trabajadores import datos_prueba as trabajadores

log = logging.getLogger("imhotep")

# El orden importa: cada paso puede depender de los anteriores.
PASOS = (
    ("almacenes", almacenes.cargar),
    ("acceso", acceso.cargar),
    ("catalogo", catalogo.cargar),
    ("trabajadores", trabajadores.cargar),
    ("movimientos", movimientos.cargar),
    ("inspecciones", inspecciones.cargar),
    ("autorizaciones", autorizaciones.cargar),
    # Depende de catálogo, movimientos e inspecciones a la vez: va al final.
    ("piezas", piezas.cargar),
)


def cargar_todo(session: Session) -> None:
    for _nombre, cargar in PASOS:
        cargar(session)


def main() -> None:
    with get_sessionmaker()() as session:
        try:
            cargar_todo(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
    print("Datos de prueba cargados:", ", ".join(nombre for nombre, _ in PASOS))


if __name__ == "__main__":
    main()
