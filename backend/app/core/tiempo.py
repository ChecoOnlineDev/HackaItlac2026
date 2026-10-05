"""Fechas: en la base van en UTC (naive) y las pone el servidor (RG-11)."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

ZONA_MX = ZoneInfo("America/Mexico_City")


def ahora_utc() -> datetime:
    """Ahora en UTC, sin zona, como se guarda en la base."""
    return datetime.now(UTC).replace(tzinfo=None)


def a_hora_mx(valor: datetime) -> datetime:
    """Convierte un datetime UTC naive de la base a hora del centro de México."""
    return valor.replace(tzinfo=UTC).astimezone(ZONA_MX)


def hoy_mx() -> date:
    """La fecha de hoy en el centro de México (vigencias de contrato e inspección)."""
    return datetime.now(ZONA_MX).date()
