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
    """El artículo ya tiene una pieza con ese número de serie (I-02)."""

    codigo = "SERIE_REPETIDA"

    mensaje_defecto = "Ya existe una pieza de ese artículo con ese número de serie."


class SerieYaRegistrada(Conflicto):
    """La pieza ya tiene número de serie: solo se pone, no se cambia (P-08)."""

    codigo = "SERIE_YA_REGISTRADA"
    mensaje_defecto = "Esta pieza ya tiene número de serie registrado."


class PiezaDeBaja(Conflicto):
    """Una pieza dada de baja ya no cambia."""

    mensaje_defecto = "La pieza está dada de baja."


class PuestoNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el puesto."


class PuestoRepetido(Conflicto):
    """Ya existe un puesto con ese nombre (sin importar mayúsculas ni acentos)."""

    mensaje_defecto = "Ya existe un puesto con ese nombre."


class EnDotacion(Conflicto):
    """El artículo está en la dotación de algún puesto: no se elimina."""

    mensaje_defecto = "El artículo está en la dotación de un puesto."
