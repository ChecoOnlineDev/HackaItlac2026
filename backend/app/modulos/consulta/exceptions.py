"""Excepciones del dominio del módulo `consulta`, sin HTTP (heredan de `app.core.excepciones`)."""

from app.core.excepciones import DatosInvalidos


class RangoFechasInvalido(DatosInvalidos):
    """La fecha inicial es posterior a la final (rango invertido)."""

    mensaje_defecto = "La fecha inicial no puede ser posterior a la fecha final."
