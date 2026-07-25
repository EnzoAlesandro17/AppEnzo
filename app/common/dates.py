from datetime import date, datetime

DATE_FORMAT = "%d-%m-%Y"


def parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FORMAT).date()


def parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return parse_date(value)
