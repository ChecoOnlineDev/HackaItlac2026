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


class RolNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el rol."


class RolExiste(Conflicto):
    """Ya hay otro rol con ese nombre."""

    codigo = "ROL_EXISTE"
    mensaje_defecto = "Ya existe un rol con ese nombre. Elige otro."


class RolProtegido(Conflicto):
    """AC-09: el rol Administrador no pierde `acceso.administrar`, no se inactiva ni se elimina; los
    roles iniciales no se eliminan ni cambian de nombre."""

    codigo = "ROL_PROTEGIDO"
    mensaje_defecto = "Ese rol está protegido y no se puede cambiar así."


class RolEnUso(Conflicto):
    """AC-11: un rol con usuarios asignados no se inactiva ni se elimina."""

    codigo = "ROL_EN_USO"
    mensaje_defecto = "Ese rol tiene usuarios asignados. Cámbiales el rol primero."


class AutoBloqueo(Conflicto):
    """AC-09: nadie se quita a sí mismo el acceso a esta pantalla."""

    codigo = "AUTO_BLOQUEO"
    mensaje_defecto = "No puedes quitarte a ti mismo el permiso de administrar el acceso."
