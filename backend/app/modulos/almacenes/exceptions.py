"""Excepciones del módulo `almacenes`."""

from typing import Any

from app.core.excepciones import Conflicto, DatosInvalidos, NoEncontrado


class AlmacenNoEncontrado(NoEncontrado):
    mensaje_defecto = "No se encontró el almacén."


class UbicacionNoEncontrada(NoEncontrado):
    mensaje_defecto = "No se encontró la ubicación."


class ClaveRepetida(Conflicto):
    """AL-02: ya hay un almacén con esa clave."""

    codigo = "CLAVE_REPETIDA"
    mensaje_defecto = "Ya hay un almacén con esa clave."


class NombreRepetido(Conflicto):
    """AL-02: ya hay un almacén con ese nombre."""

    codigo = "NOMBRE_REPETIDO"
    mensaje_defecto = "Ya hay un almacén con ese nombre."


class YaHayCentral(Conflicto):
    """AL-02: solo hay un almacén central."""

    codigo = "YA_HAY_CENTRAL"
    mensaje_defecto = "Ya existe el almacén central; solo puede haber uno."


class ClaveConFolios(Conflicto):
    """AL-05: la clave forma parte de los folios ya emitidos."""

    codigo = "CLAVE_CON_FOLIOS"
    mensaje_defecto = "La clave no se puede cambiar: el almacén ya tiene folios."


class PadreCerrado(Conflicto):
    """AL-03: no se reactiva un almacén cuyo padre está cerrado."""

    codigo = "PADRE_CERRADO"
    mensaje_defecto = "Primero reactiva el almacén del que depende."


class PadreInvalido(DatosInvalidos):
    """AL-02: el padre no existe, está cerrado, es el mismo almacén o un descendiente, o el tipo
    no cuadra con tener padre."""

    codigo = "PADRE_INVALIDO"
    mensaje_defecto = "El almacén del que depende no es válido."

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo, {"regla": "AL-02", "motivo": motivo})


class AlmacenCerrado(Conflicto):
    """AL-04: un almacén cerrado no recibe ni envía movimientos ni solicitudes nuevas."""

    codigo = "ALMACEN_CERRADO"
    mensaje_defecto = "Ese almacén está cerrado."

    def __init__(self, almacen: Any = None, mensaje: str | None = None) -> None:
        detalles: dict[str, Any] = {"regla": "AL-04"}
        if almacen is not None:
            detalles["almacen"] = {
                "id": str(almacen.id),
                "clave": almacen.clave,
                "nombre": almacen.nombre,
            }
        super().__init__(mensaje, detalles)


class AlmacenConBloqueos(Conflicto):
    """AL-03: no se puede inactivar. El `codigo` es el del primer bloqueo."""

    def __init__(self, mensaje: str, bloqueos: list[dict[str, Any]]) -> None:
        self.codigo = bloqueos[0]["codigo"]
        super().__init__(mensaje, {"regla": "AL-03", "bloqueos": bloqueos})
