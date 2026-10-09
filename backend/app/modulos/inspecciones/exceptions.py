"""Excepciones del dominio, sin HTTP (heredan de app.core.excepciones).

Los códigos están mapeados a su estado HTTP en `app/core/handlers.py`.
"""

from app.core.excepciones import Conflicto, DatosInvalidos, SinPermiso


class AjustePropio(SinPermiso):
    """P-07: quien registró la inspección no puede ajustar su vigencia (403)."""

    codigo = "AJUSTE_PROPIO"
    mensaje_defecto = "No puedes ajustar la vigencia de una inspección que tú registraste."


class AjusteNoPermitido(Conflicto):
    """P-07: la pieza no admite el ajuste (No apta, sin inspección vigente o dada de baja)."""

    codigo = "AJUSTE_NO_PERMITIDO"
    mensaje_defecto = "La vigencia de esta pieza no se puede ajustar."


class VigenciaExcedida(DatosInvalidos):
    """P-07: alargar la vigencia más allá de la inspección más la vigencia del artículo (422)."""

    codigo = "VIGENCIA_EXCEDIDA"
    mensaje_defecto = "La vigencia no puede pasar de la fecha de la inspección más la del artículo."


class PiezaEnBaja(Conflicto):
    """Una pieza dada de baja ya no se inspecciona ni cambia de estado."""

    mensaje_defecto = "La pieza está dada de baja."


class EstadoSinCambio(Conflicto):
    """Marcar No apta a una pieza que ya lo está."""

    mensaje_defecto = "La pieza ya estaba como No apta."


class PiezaEnTransito(Conflicto):
    codigo = "PIEZA_EN_TRANSITO"
    mensaje_defecto = "La pieza está en tránsito. Recíbela antes de inspeccionarla."


class PiezaEnMantenimiento(Conflicto):
    codigo = "PIEZA_EN_MANTENIMIENTO"
    mensaje_defecto = "La pieza debe salir de mantenimiento o calibración antes de inspeccionarla."


class FechaFutura(DatosInvalidos):
    codigo = "FECHA_FUTURA"
    mensaje_defecto = "La fecha de inspección no puede estar en el futuro."
