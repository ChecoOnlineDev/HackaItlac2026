"""Excepciones del módulo `archivos`."""

from app.core.excepciones import DatosInvalidos, NoEncontrado


class ArchivoInvalido(DatosInvalidos):
    """Tipo no permitido, vacío o demasiado grande."""

    mensaje_defecto = "El archivo no es válido."


class AdjuntoNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el archivo."
