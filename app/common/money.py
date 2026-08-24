def parse_amount(value: str) -> float:
    cleaned = value.strip()
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    return float(cleaned)


def format_amount(value: float) -> str:
    negative = value < 0
    value = abs(value)
    formatted = f"{value:,.2f}"
    integer_part, decimal_part = formatted.split(".")
    integer_part = integer_part.replace(",", ".")
    sign = "-" if negative else ""
    return f"{sign}$ {integer_part},{decimal_part}"
