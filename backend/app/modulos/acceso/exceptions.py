"""Excepciones del módulo `acceso`. No dependen de HTTP."""

from app.core.excepciones import AppError, Conflicto, NoAutenticado, NoEncontrado


class CredencialesIncorrectas(NoAutenticado):
    """Usuario o contraseña incorrectos; no dice cuál falló ni si el usuario está inactivo."""

    mensaje_defecto = "Usuario o contraseña incorrectos"


class PinIncorrecto(AppError):
    """El PIN no es válido. Se responde 403 (no 401, para no cerrar la sesión en la interfaz)."""

    codigo = "PIN_INCORRECTO"
    mensaje_defecto = "PIN incorrecto."


class UsuarioNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el usuario."


class UsuarioExiste(Conflicto):
    """El nombre de usuario ya lo usa otra persona."""

    codigo = "USUARIO_EXISTE"
    mensaje_defecto = "Ese usuario ya existe. Elige otro."


class UltimoAdministrador(Conflicto):
    """AC-09: siempre queda al menos un usuario activo con `acceso.administrar`."""

    codigo = "ULTIMO_ADMINISTRADOR"
    mensaje_defecto = (
        "Debe quedar al menos un administrador activo. Asigna ese permiso a otro usuario primero."
    )


class AlmacenCambio(Conflicto):
    """AC-13: el vale se capturó en un almacén que ya no es el del usuario."""

    codigo = "ALMACEN_CAMBIO"
    mensaje_defecto = (
        "Tu almacén cambió mientras capturabas. No se guardó el vale; "
        "revisa el borrador en tu almacén actual."
    )
