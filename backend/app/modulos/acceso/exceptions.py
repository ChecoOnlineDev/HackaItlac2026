"""Excepciones del módulo `acceso`. No dependen de HTTP."""

from app.core.excepciones import AppError, NoAutenticado


class CredencialesIncorrectas(NoAutenticado):
    """Usuario o contraseña incorrectos; no dice cuál falló ni si el usuario está inactivo."""

    mensaje_defecto = "Usuario o contraseña incorrectos"


class PinIncorrecto(AppError):
    """El PIN no es válido. Se responde 403 (no 401, para no cerrar la sesión en la interfaz)."""

    codigo = "PIN_INCORRECTO"
    mensaje_defecto = "PIN incorrecto."
