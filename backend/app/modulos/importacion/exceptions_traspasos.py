"""Excepciones propias de la importacion de traspasos (FEAT-009), sin HTTP.

`ARCHIVO_REPETIDO`, `LoteEnUso` y `ArchivoInvalido` son los de la importacion de entradas
(`exceptions.py`); `RUTA_SOLO_ADMINISTRADOR` y `ALMACEN_CERRADO` los de movimientos y almacenes.
"""

from app.core.excepciones import Conflicto, DatosInvalidos


class TraspasoMuyGrande(DatosInvalidos):
    """TR-07: mas de 500 renglones. Un traspaso no se parte en varios vales."""

    codigo = "TRASPASO_MUY_GRANDE"
    mensaje_defecto = (
        "El traspaso trae más de 500 renglones. Divide el archivo en varios y sube cada uno por "
        "separado."
    )


class FilasConError(Conflicto):
    """TR-06: hay filas en rojo y no se pidio dejarlas fuera; no se guardo nada (RG-09)."""

    codigo = "FILAS_CON_ERROR"
    mensaje_defecto = (
        "Hay filas con error y no se guardó nada. Corrige el archivo o elige dejar fuera las "
        "filas con error."
    )
