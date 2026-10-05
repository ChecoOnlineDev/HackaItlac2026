"""Excepciones del módulo `catalogo`. No dependen de HTTP (heredan de `app.core.excepciones`)."""

from app.core.excepciones import Conflicto, NoEncontrado


class CategoriaNoEncontrada(NoEncontrado):
    mensaje_defecto = "No se encontró la categoría."


class ArticuloNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el artículo."


class PiezaNoEncontrada(NoEncontrado):
    mensaje_defecto = "No se encontró la pieza."


class ConMovimientos(Conflicto):
    """El artículo ya tiene movimientos (CF-05, CF-12): no se elimina ni cambia su control."""

    codigo = "CON_MOVIMIENTOS"
    mensaje_defecto = "El artículo ya tiene movimientos."


class EstadoRepetido(Conflicto):
    """Inactivar a quien ya está inactivo, reactivar a quien ya está activo."""

    mensaje_defecto = "Ese cambio ya estaba hecho."


class NombreRepetido(Conflicto):
    """Ya existe una categoría con ese nombre (CF-01)."""

    mensaje_defecto = "Ya existe una categoría con ese nombre."


class SerieRepetida(Conflicto):
    """El artículo ya tiene una pieza con ese número de serie."""

    mensaje_defecto = "Ya existe una pieza de ese artículo con ese número de serie."
