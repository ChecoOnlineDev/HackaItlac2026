"""Exportación a CSV de los reportes: codificación para Excel y neutralización de fórmulas.

Solo usa el módulo `csv` de la biblioteca estándar. El archivo sale en `utf-8-sig` (con BOM) para
que Excel abra bien los acentos.
"""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any

from fastapi import Response

from app.core.tiempo import a_hora_mx

# Una celda de texto que empieza con alguno de estos caracteres la interpreta Excel como fórmula.
_INICIOS_PELIGROSOS = ("=", "+", "-", "@", "\t", "\r")

MEDIA_TYPE_CSV = "text/csv; charset=utf-8"


def neutralizar(valor: str) -> str:
    """Antepone una comilla simple al texto que Excel tomaría por fórmula (inyección)."""
    if valor.lstrip().startswith(_INICIOS_PELIGROSOS):
        return "'" + valor
    return valor


def texto_fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def texto_fecha_hora(valor_utc: datetime) -> str:
    """Una fecha y hora UTC (naive, como se guarda) en la hora del centro de México."""
    if valor_utc.tzinfo is not None:
        valor_utc = valor_utc.astimezone(UTC).replace(tzinfo=None)
    return a_hora_mx(valor_utc).strftime("%d/%m/%Y %H:%M:%S")


def _celda(valor: Any) -> Any:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, datetime):
        return texto_fecha_hora(valor)
    if isinstance(valor, date):
        return texto_fecha(valor)
    if isinstance(valor, str):
        return neutralizar(valor)
    return valor


def construir_csv(encabezados: Sequence[str], filas: Iterable[Sequence[Any]]) -> bytes:
    """El CSV completo en bytes `utf-8-sig`. Los encabezados son fijos (no vienen del usuario)."""
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow(encabezados)
    for fila in filas:
        escritor.writerow([_celda(v) for v in fila])
    return salida.getvalue().encode("utf-8-sig")


def respuesta_csv(contenido: bytes, nombre_archivo: str) -> Response:
    return Response(
        content=contenido,
        media_type=MEDIA_TYPE_CSV,
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
