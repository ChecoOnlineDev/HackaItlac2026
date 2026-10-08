"""Plantilla `.xlsx` de ejemplo para cada modo de la importacion (I-10).

Trae los encabezados que `proponer_columnas` reconoce, una fila de ejemplo y una hoja de
instrucciones. No lee ni escribe datos del sistema. La columna de costo solo viene en `ALTA` y
solo para quien tiene `catalogo.costos` (RG-12, I-04).
"""

import io

from openpyxl import Workbook
from openpyxl.styles import Font

# (encabezado, ejemplo, ayuda), en el orden de las columnas.
_ALTA = (
    ("Código", "MART-01", "Código del artículo. Si lo dejas vacío, el sistema lo genera."),
    ("Nombre", "Martillo de bola 16 oz", "Obligatorio en los artículos nuevos."),
    ("Marca", "Truper", "Opcional."),
    ("Categoría", "Herramienta manual", "Si la dejas vacía, el sistema sugiere una."),
    ("Cantidad", 12, "Número entero, hasta el tope por fila."),
    ("Unidad", "pieza", "Opcional, hasta 20 caracteres. Solo se usa al crear el artículo."),
    ("Serie", "", "Solo para artículos por pieza. Vacía: la serie queda pendiente."),
    (
        "Código de la pieza",
        "",
        "Solo para artículos por pieza. Vacío: el sistema lo genera al confirmar.",
    ),
)
_COSTO = ("Costo", 85.5, "Costo unitario del artículo nuevo. Solo con permiso de costos.")
_REPOSICION = (
    ("Código", "MART-01", "Código de un artículo que ya existe. Obligatorio."),
    ("Cantidad", 12, "Número entero, hasta el tope por fila."),
    ("Serie", "", "Solo para artículos por pieza."),
    ("Código de la pieza", "", "Solo para artículos por pieza: una fila por pieza."),
)

_NOTAS = {
    "ALTA": (
        "Alta: crea los artículos nuevos y suma a los que ya existen.",
        "Las filas del mismo artículo se unen en una.",
        "Todo entra a Kepler; de ahí se reparte por traspaso.",
        "Sin serie, la pieza entra con la serie pendiente; sin código de pieza, se genera.",
        "La cantidad es un número entero: en lugar de 0.25 kilos, escribe 250 gramos.",
        "Una fila cuya descripción dice SERVICIO no es un artículo y se excluye.",
    ),
    "REPOSICION": (
        "Reposición: solo suma a artículos que ya existen; nunca crea.",
        "Un código que no existe es un error: dalo de alta primero.",
        "Las columnas de nombre, marca, categoría y costo no se leen.",
        "Todo entra a Kepler; de ahí se reparte por traspaso.",
        "La cantidad es un número entero: en lugar de 0.25 kilos, escribe 250 gramos.",
    ),
}


def generar_plantilla(modo: str, *, con_costo: bool) -> bytes:
    """El archivo de ejemplo de ese modo, en bytes."""
    columnas = list(_REPOSICION if modo == "REPOSICION" else _ALTA)
    if modo != "REPOSICION" and con_costo:
        columnas.insert(6, _COSTO)  # junto a la cantidad
    libro = Workbook()
    hoja = libro.active
    assert hoja is not None
    hoja.title = "Plantilla"
    hoja.append([c[0] for c in columnas])
    hoja.append([c[1] for c in columnas])
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for indice, columna in enumerate(columnas, start=1):
        hoja.column_dimensions[hoja.cell(row=1, column=indice).column_letter].width = max(
            14, len(columna[0]) + 4
        )
    ayuda = libro.create_sheet("Instrucciones")
    ayuda.append(["Dato", "Qué poner"])
    for celda in ayuda[1]:
        celda.font = Font(bold=True)
    for encabezado, _, texto in columnas:
        ayuda.append([encabezado, texto])
    ayuda.append([])
    for nota in _NOTAS.get(modo, _NOTAS["ALTA"]):
        ayuda.append([nota])
    ayuda.column_dimensions["A"].width = 24
    ayuda.column_dimensions["B"].width = 80
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()
