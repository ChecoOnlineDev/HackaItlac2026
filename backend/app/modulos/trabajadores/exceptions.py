"""Excepciones del módulo `trabajadores`. No dependen de HTTP."""

from app.core.excepciones import Conflicto, DatosInvalidos, NoEncontrado


class TrabajadorNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró al trabajador."


class TrabajadorSinFoto(NoEncontrado):
    mensaje_defecto = "Sin foto registrada."


class TrabajadorExiste(Conflicto):
    """El número de empleado o la CURP ya son de alguien (T-02). `detalles` trae a la persona
    para ofrecer el reingreso."""

    codigo = "TRABAJADOR_EXISTE"
    mensaje_defecto = "Ya existe un trabajador con esos datos."


class PeriodoInvalido(DatosInvalidos):
    """La fecha de fin es anterior a la de inicio (T-03)."""

    mensaje_defecto = "La fecha de fin no puede ser anterior a la de inicio."


class EstadoTrabajadorInvalido(Conflicto):
    """La operación no aplica al estado actual del trabajador (T-06)."""

    mensaje_defecto = "Esa acción no aplica al estado actual del trabajador."


class TrabajadorConPendientes(Conflicto):
    """Tiene retornables en resguardo (B-02, B-04). `detalles` trae los pendientes."""

    codigo = "CON_PENDIENTES"
    mensaje_defecto = "El trabajador todavía tiene equipo pendiente de devolver."
