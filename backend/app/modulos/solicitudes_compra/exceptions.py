"""Excepciones del módulo `solicitudes_compra`. No dependen de HTTP.

Los códigos están mapeados a su estado HTTP en `app/core/handlers.py`. Cada una lleva en
`detalles` el ID de la regla que la originó (`{"regla": "SC-04", ...}`).
"""

from typing import Any

from app.core.excepciones import Conflicto, NoEncontrado, SinPermiso


class SolicitudNoEncontrada(NoEncontrado):
    """No existe, o es de un almacén que el usuario no ve (AC-06, SC-03)."""

    mensaje_defecto = "No se encontró la solicitud de compra."


class TransicionInvalida(Conflicto):
    """SC-04: la solicitud no puede pasar a ese estado desde el que tiene."""

    codigo = "TRANSICION_INVALIDA"
    mensaje_defecto = "La solicitud no puede pasar a ese estado."

    def __init__(self, actual: str, pedido: str, permitidos: list[str]) -> None:
        if permitidos:
            sigue = "Desde ahí solo puede pasar a: " + ", ".join(permitidos) + "."
        else:
            sigue = "Ya está cerrada y no cambia más."
        super().__init__(
            f"La solicitud está {actual} y no puede pasar a {pedido}. {sigue} (SC-04)",
            {
                "regla": "SC-04",
                "estado_actual": actual,
                "estado_pedido": pedido,
                "estados_permitidos": permitidos,
            },
        )


class SolicitudNoCancelable(Conflicto):
    """SC-07: solo se cancela mientras sigue pendiente. Usa el código `NO_CANCELABLE`, el mismo
    de los vales."""

    codigo = "NO_CANCELABLE"

    def __init__(self, actual: str) -> None:
        super().__init__(
            f"La solicitud ya está {actual}: solo se cancela mientras está PENDIENTE. (SC-07)",
            {"regla": "SC-07", "estado_actual": actual},
        )


class SinPermisoParaCancelar(SinPermiso):
    """SC-07: la cancela quien la pidió, un supervisor de su almacén o el Administrador."""

    def __init__(self) -> None:
        super().__init__(
            "Solo quien la pidió, un supervisor de su almacén o el administrador puede "
            "cancelar la solicitud. (SC-07)",
            {"regla": "SC-07"},
        )


class IdClienteEnUso(Conflicto):
    """SC-10: el `id_cliente` ya identifica la solicitud de otro usuario."""

    codigo = "ID_CLIENTE_EN_USO"

    def __init__(self) -> None:
        super().__init__(
            "Ese identificador de solicitud ya se usó para otra operación. (SC-10)",
            {"regla": "SC-10"},
        )


class IdClienteOtroCuerpo(Conflicto):
    """SC-10: el `id_cliente` ya creó una solicitud, pero con datos distintos."""

    codigo = "ID_CLIENTE_EN_USO"

    def __init__(self) -> None:
        super().__init__(
            "Esa solicitud ya se guardó antes con otros datos. Revisa lo capturado o empieza "
            "una solicitud nueva. (SC-10)",
            {"regla": "SC-10"},
        )


def detalle_campo(campo: str, mensaje: str, regla: str) -> list[dict[str, Any]]:
    """Forma de `detalles` de un 422: `[{campo, mensaje, regla}]`."""
    return [{"campo": campo, "mensaje": mensaje, "regla": regla}]
