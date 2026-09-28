"""
Fecha y hora del hospital. Argentina usa UTC-3 todo el año (sin horario de verano),
así que se usa un desfase fijo y no hace falta instalar la base de zonas horarias en Windows.
"""
from datetime import date, datetime, time, timedelta, timezone

ZONA = timezone(timedelta(hours=-3), "ART")


def ahora() -> datetime:
    """Fecha y hora actuales en la zona del hospital."""
    return datetime.now(ZONA)


def hoy() -> date:
    """Fecha actual en la zona del hospital (no la del servidor en UTC)."""
    return ahora().date()


def rango_del_dia(fecha: date) -> tuple[datetime, datetime]:
    """Inicio y fin de un día en la zona del hospital, para filtrar columnas con hora."""
    return datetime.combine(fecha, time.min, tzinfo=ZONA), datetime.combine(fecha, time.max, tzinfo=ZONA)
