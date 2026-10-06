"""Excepciones del dominio, sin HTTP (heredan de app.core.excepciones).

Modulo `importacion`. Los codigos estan mapeados a su estado HTTP en `app/core/handlers.py`.
"""

from datetime import UTC, datetime

from app.core.excepciones import Conflicto, DatosInvalidos


class ArchivoInvalido(DatosInvalidos):
    """El archivo subido no se puede leer como una tabla de Excel (.xlsx). Nunca es un 500."""

    mensaje_defecto = "No se pudo leer el archivo. Sube un Excel con extensión .xlsx."


class SinFilasValidas(DatosInvalidos):
    """La importacion no tiene ninguna fila que se pueda guardar."""

    mensaje_defecto = "No hay filas válidas para importar. Corrige los errores y vuelve a intentar."


class LoteEnUso(Conflicto):
    """El `id_lote` ya lo uso otra persona."""

    mensaje_defecto = "Ese lote de importación ya lo usó otra persona."


class ImportacionCambio(Conflicto):
    """Al confirmar, algo cambio desde la vista previa y no se guardo nada (RG-09)."""

    mensaje_defecto = (
        "Los datos cambiaron mientras revisabas la importación. No se guardó nada: "
        "vuelve a revisar la vista previa."
    )


class ArchivoRepetido(Conflicto):
    """El mismo archivo ya se importó (I-12): se pide confirmar de nuevo de forma expresa."""

    codigo = "ARCHIVO_REPETIDO"
    mensaje_defecto = (
        "Este archivo ya se importó antes. Si quieres importarlo otra vez, confirma de nuevo."
    )

    def __init__(self, fecha: datetime) -> None:
        super().__init__(
            detalles={
                "regla": "I-12",
                "fecha": fecha.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            }
        )
