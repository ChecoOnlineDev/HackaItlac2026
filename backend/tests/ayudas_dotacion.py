"""Ayudas de las pruebas de la dotación por puesto (FEAT-003).

La línea base de las pruebas no trae dotaciones (`conftest.engine` las quita): cada prueba arma la
suya con `dotacion_de_prueba`, que crea un puesto nuevo, le pone su dotación y lo liga al periodo
vigente del trabajador.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.catalogo.models import Articulo, Dotacion, Puesto
from app.modulos.trabajadores.models import PeriodoContrato, Trabajador


def puesto_de_prueba(
    session: Session, dotacion: dict[Articulo, int] | None = None, *, activo: bool = True
) -> Puesto:
    """Un puesto con nombre único y la dotación indicada (`{articulo: cantidad}`)."""
    puesto = Puesto(nombre=f"Puesto {uuid.uuid4().hex[:8]}", activo=activo)
    session.add(puesto)
    session.flush()
    for articulo, cantidad in (dotacion or {}).items():
        session.add(Dotacion(puesto_id=puesto.id, articulo_id=articulo.id, cantidad=cantidad))
    session.flush()
    return puesto


def asignar_puesto(session: Session, trabajador: Trabajador, puesto: Puesto) -> None:
    """Liga todos los periodos del trabajador a `puesto` (y deja su nombre en el texto)."""
    for periodo in session.scalars(
        select(PeriodoContrato).where(PeriodoContrato.trabajador_id == trabajador.id)
    ):
        periodo.puesto_id = puesto.id
        periodo.puesto = puesto.nombre
    session.flush()


def dotacion_de_prueba(
    session: Session, trabajador: Trabajador, dotacion: dict[Articulo, int]
) -> Puesto:
    """Crea un puesto con esa dotación y se lo da al trabajador."""
    puesto = puesto_de_prueba(session, dotacion)
    asignar_puesto(session, trabajador, puesto)
    return puesto
