"""Excepciones base del dominio. No dependen de HTTP: el handler global las traduce."""

from typing import Any


class AppError(Exception):
    """Fallo esperado. `codigo` es el de la tabla de errores de api-contracts.md."""

    codigo: str = "ERROR"
    mensaje_defecto: str = "Ocurrió un error."

    def __init__(self, mensaje: str | None = None, detalles: Any = None) -> None:
        self.mensaje = mensaje or self.mensaje_defecto
        self.detalles = detalles
        super().__init__(self.mensaje)


class NoAutenticado(AppError):
    codigo = "NO_AUTENTICADO"
    mensaje_defecto = "Inicia sesión para continuar."


class SinPermiso(AppError):
    codigo = "SIN_PERMISO"
    mensaje_defecto = "Tu rol no puede hacer esto."


class NoEncontrado(AppError):
    codigo = "NO_ENCONTRADO"
    mensaje_defecto = "No se encontró lo que buscas."


class DatosInvalidos(AppError):
    codigo = "DATOS_INVALIDOS"
    mensaje_defecto = "Revisa los datos capturados."


class DemasiadosIntentos(AppError):
    codigo = "DEMASIADOS_INTENTOS"

    def __init__(self, segundos: int, mensaje: str | None = None) -> None:
        minutos = max(1, -(-segundos // 60))
        super().__init__(
            mensaje or f"Demasiados intentos. Espera {minutos} min para volver a intentar.",
            {"segundos_espera": segundos},
        )
        self.segundos = segundos


class ServicioOcupado(AppError):
    """La base de datos canceló la operación por un choque entre transacciones y no se pudo
    repetir a tiempo (503). Es transitorio: intentar de nuevo suele funcionar."""

    codigo = "SERVICIO_NO_DISPONIBLE"
    mensaje_defecto = "El servicio está ocupado en este momento. Intenta de nuevo."


class Conflicto(AppError):
    """Base de los 409. Cada módulo define su subclase con su `codigo`
    (VALE_CAMBIO, ALMACEN_CAMBIO, CODIGO_REPETIDO, CON_PENDIENTES, CON_MOVIMIENTOS,
    NO_CANCELABLE); todos ya están mapeados a 409 en `core/handlers.py`."""

    codigo = "CONFLICTO"
    mensaje_defecto = "La operación entra en conflicto con el estado actual."
