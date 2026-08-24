from datetime import date, datetime

DATE_FORMAT = "%d-%m-%Y"

WEEKDAYS_ES = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]

MONTHS_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FORMAT).date()


def parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return parse_date(value)


def format_day_label(value: date) -> str:
    """Ej. 'Lunes 24-08-2026'. No depende del locale del sistema."""
    return f"{WEEKDAYS_ES[value.weekday()]} {value.strftime(DATE_FORMAT)}"


def format_long_date_es(value: date) -> str:
    """Ej. 'lunes 24 de agosto de 2026'. No depende del locale del sistema."""
    weekday = WEEKDAYS_ES[value.weekday()].lower()
    month = MONTHS_ES[value.month - 1]
    return f"{weekday} {value.day} de {month} de {value.year}"


def format_month_es(value: date) -> str:
    """Ej. 'Septiembre 2026'. No depende del locale del sistema."""
    month = MONTHS_ES[value.month - 1].capitalize()
    return f"{month} {value.year}"
