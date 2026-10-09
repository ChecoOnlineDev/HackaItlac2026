"""Avisos puros de mínimo disponible (E-14, X-05); nunca bloquean."""


def regla_minimo(regla: str, minimo: int | None, disponible: int, salida: int):
    from app.modulos.movimientos.evaluador import Motivo
    from app.modulos.movimientos.models import Nivel

    restante = disponible - salida
    if minimo is None or salida <= 0 or restante >= minimo:
        return None
    return Motivo(
        regla,
        Nivel.AMARILLO,
        f"Quedarían {max(0, restante)} disponibles; el mínimo del almacén es {minimo}.",
    )
