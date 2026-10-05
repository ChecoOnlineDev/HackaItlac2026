"""Excepciones del dominio, sin HTTP (heredan de app.core.excepciones).

Los códigos están mapeados a su estado HTTP en `app/core/handlers.py`.
"""

from app.core.excepciones import AppError, Conflicto, SinPermiso


class AutorizacionPropia(SinPermiso):
    """A-05 / AC-07: quien captura el vale no puede autorizarse a sí mismo (403)."""

    codigo = "AUTORIZACION_PROPIA"
    mensaje_defecto = "No puedes autorizar una solicitud que tú mismo pediste."


class AutorizacionResuelta(Conflicto):
    """La solicitud ya no está pendiente: se resolvió o venció (409)."""

    codigo = "AUTORIZACION_RESUELTA"
    mensaje_defecto = "Esta solicitud ya no está pendiente."


class AutorizacionInvalida(Conflicto):
    """La autorización no sirve para este vale: no está aprobada, venció, ya se usó o no cubre
    los renglones (A-03). Siempre 409; el mensaje dice la causa."""

    codigo = "AUTORIZACION_INVALIDA"
    mensaje_defecto = "La autorización no sirve para este vale."


class RenglonNoAutorizable(AppError):
    """A-06: un renglón en rojo no se puede enviar a autorización (422)."""

    codigo = "RENGLON_NO_AUTORIZABLE"
    mensaje_defecto = "Un renglón en rojo no se puede enviar a autorización."
