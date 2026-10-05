"""Excepciones del módulo `almacenes`."""

from app.core.excepciones import NoEncontrado


class AlmacenNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el almacén."


class UbicacionNoEncontrada(NoEncontrado):
    mensaje_defecto = "No se encontró la ubicación."
