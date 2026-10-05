"""Excepciones del dominio, sin HTTP (heredan de app.core.excepciones).

Los códigos están mapeados a su estado HTTP en `app/core/handlers.py`.
"""

from app.core.excepciones import AppError, Conflicto, DatosInvalidos, NoEncontrado


class ValeNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el vale."


class ValeCambio(Conflicto):
    """RG-08: al confirmar, la evaluación ya no es la misma (o quedó un rojo o un naranja sin
    autorizar). `detalles` trae la evaluación nueva. El vale no se guardó."""

    codigo = "VALE_CAMBIO"
    mensaje_defecto = "El vale cambió mientras lo capturabas. Revisa los renglones marcados."


class AlmacenCambio(Conflicto):
    """AC-13: el usuario ya no está asignado al almacén en el que capturó el vale."""

    codigo = "ALMACEN_CAMBIO"
    mensaje_defecto = "Cambiaste de almacén. El vale no se guardó; tu borrador se conserva."


class IdClienteEnUso(Conflicto):
    """El `id_cliente` ya identifica el vale de otro usuario u otro tipo."""

    mensaje_defecto = "Ese identificador de vale ya se usó para otra operación."


class IdClienteOtroCuerpo(Conflicto):
    """El `id_cliente` ya confirmó un vale, pero con un cuerpo DISTINTO: no se devuelve ese vale
    como si fuera lo que se acaba de pedir."""

    mensaje_defecto = (
        "Ese vale ya se guardó antes con otros datos. Revisa lo capturado o empieza un vale nuevo."
    )


class ExistenciaInsuficiente(Conflicto):
    """RG-04: una salida dejaría la existencia en negativo. Red de seguridad: la evaluación
    ya la detecta antes (E-04), así que solo ocurre si algo se saltó los bloqueos."""

    mensaje_defecto = "No hay existencia suficiente para registrar el movimiento."


class FirmaRequerida(DatosInvalidos):
    """F-02: una entrega sin la firma del trabajador se rechaza."""

    mensaje_defecto = "Falta la firma del trabajador."


class TipoNoImplementado(AppError):
    """El tipo de vale está registrado pero su archivo en `tipos/` aún es un stub (501)."""

    codigo = "TIPO_NO_IMPLEMENTADO"
    mensaje_defecto = "Esta operación todavía no está disponible."


class NoCancelable(Conflicto):
    """K-03, K-04, X-14: el vale no se puede cancelar. No se escribió nada. `detalles` trae, por
    cada motivo, `{regla, mensaje}` (y `renglon` y `codigo` si es de un renglón)."""

    codigo = "NO_CANCELABLE"
    mensaje_defecto = "Este vale no se puede cancelar."
