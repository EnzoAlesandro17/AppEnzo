from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.cards import models
from app.common.ids import generate_id

CURRENCIES = ("ARS", "USD")


def _shift_period(period: date, months: int) -> date:
    total_months = period.year * 12 + (period.month - 1) + months
    year, month = divmod(total_months, 12)
    return date(year, month + 1, 1)


def _current_period() -> date:
    today = date.today()
    return date(today.year, today.month, 1)


def statement_status(period: date) -> str:
    current = _current_period()
    if period < current:
        return "closed"
    if period > current:
        return "future"
    return "open"


def _start_date_for(card_id: str, period: date) -> date | None:
    """El inicio de un resumen es el día siguiente al cierre del resumen del
    período anterior. No asume que el primer período sea el más viejo: puede
    haber resúmenes históricos con períodos previos a cualquiera existente."""
    previous = models.get_statement_by_period(card_id, _shift_period(period, -1))
    if previous is None or previous["closing_date"] is None:
        return None
    return previous["closing_date"] + timedelta(days=1)


def create_card(user_id: str, name: str, bank: str | None, last_four_digits: str | None) -> str:
    card_id = generate_id()
    models.create_card(card_id, user_id, name, bank, last_four_digits)
    statement_id = generate_id()
    models.insert_statement(statement_id, card_id, _current_period())
    return card_id


def list_cards(user_id: str) -> list[dict]:
    return models.list_cards(user_id)


def get_card(card_id: str, user_id: str) -> dict | None:
    return models.get_card(card_id, user_id)


def _get_or_create_statement(card_id: str, period: date) -> dict:
    statement = models.get_statement_by_period(card_id, period)
    if statement is not None:
        return statement
    statement_id = generate_id()
    models.insert_statement(statement_id, card_id, period)
    return models.get_statement_by_period(card_id, period)


def get_statement(card_id: str, statement_id: str) -> dict | None:
    return models.get_statement(statement_id, card_id)


def get_current_statement(card_id: str) -> dict:
    return _get_or_create_statement(card_id, _current_period())


def _statement_for_date(card_id: str, entry_date: date) -> dict:
    """Resuelve a qué resumen pertenece una fecha, según los cierres ya
    confirmados (contiguos, sin saltos). Si no hay cierre que la delimite
    (típicamente el mes en curso o uno futuro sin datos todavía), cae en el
    resumen de su mes calendario."""
    statements = sorted(models.list_statements(card_id), key=lambda s: s["period"])
    previous_closing: date | None = None
    for statement in statements:
        if statement["closing_date"] is not None:
            if entry_date <= statement["closing_date"] and (
                previous_closing is None or entry_date > previous_closing
            ):
                return statement
            previous_closing = statement["closing_date"]
    return _get_or_create_statement(card_id, date(entry_date.year, entry_date.month, 1))


def add_expense(card_id: str, currency: str, amount: Decimal, description: str | None, entry_date: date) -> dict:
    statement = _statement_for_date(card_id, entry_date)
    models.insert_entry(generate_id(), card_id, statement["id"], "expense", currency, amount, description, entry_date)
    return statement


def add_payment(card_id: str, currency: str, amount: Decimal, description: str | None, entry_date: date) -> dict:
    statement = _statement_for_date(card_id, entry_date)
    models.insert_entry(generate_id(), card_id, statement["id"], "payment", currency, amount, description, entry_date)
    return statement


def _split_amount(total: Decimal, count: int) -> list[Decimal]:
    base = (total / count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amounts = [base] * count
    remainder = total - (base * count)
    amounts[-1] += remainder
    return amounts


def add_installment_purchase(
    card_id: str,
    currency: str,
    total_amount: Decimal,
    installment_count: int,
    description: str | None,
    purchase_date: date,
) -> dict:
    first_statement = _statement_for_date(card_id, purchase_date)

    plan_id = generate_id()
    models.insert_installment_plan(
        plan_id, card_id, currency, total_amount, installment_count, description, purchase_date
    )

    amounts = _split_amount(total_amount, installment_count)
    for installment_number, amount in enumerate(amounts, start=1):
        # Solo la 1ra cuota se resuelve por fecha; las siguientes son
        # consecuentes por período, la fecha ahí es una formalidad.
        period = _shift_period(first_statement["period"], installment_number - 1)
        statement = _get_or_create_statement(card_id, period)
        entry_description = f"{description} ({installment_number}/{installment_count})" if description else None
        models.insert_entry(
            generate_id(),
            card_id,
            statement["id"],
            "expense",
            currency,
            amount,
            entry_description,
            purchase_date,
            installment_plan_id=plan_id,
            installment_number=installment_number,
        )
    return first_statement


def create_statement_for_period(card_id: str, year: int, month: int) -> dict:
    return _get_or_create_statement(card_id, date(year, month, 1))


def delete_entry(card_id: str, entry_id: str) -> None:
    entry = models.get_entry(entry_id, card_id)
    if entry is None:
        raise ValueError("entry not found")
    models.soft_delete_entry(entry_id)


def delete_statement(card_id: str, statement_id: str) -> None:
    statement = models.get_statement(statement_id, card_id)
    if statement is None:
        raise ValueError("statement not found")
    if models.count_entries_for_statement(statement_id) > 0:
        raise ValueError("statement has entries")
    models.soft_delete_statement(statement_id)


def _entries_with_balance(card_id: str) -> list[dict]:
    entries = models.list_entries_for_card(card_id)
    running = {currency: Decimal("0") for currency in CURRENCIES}
    result = []
    for entry in entries:
        sign = -1 if entry["entry_type"] == "payment" else 1
        running[entry["currency"]] += sign * entry["amount"]
        result.append({**entry, "balance_after": running[entry["currency"]]})
    return result


def list_entries_page(card_id: str, page: int, per_page: int = 50) -> dict:
    entries = list(reversed(_entries_with_balance(card_id)))
    start = (page - 1) * per_page
    page_entries = entries[start : start + per_page]
    return {
        "entries": page_entries,
        "page": page,
        "has_next": start + per_page < len(entries),
        "has_prev": page > 1,
    }


def list_statements(card_id: str) -> list[dict]:
    statements = models.list_statements(card_id)

    expense_totals_by_statement: dict[str, dict[str, Decimal]] = {}
    for entry in models.list_entries_for_card(card_id):
        if entry["entry_type"] not in ("expense", "charge"):
            continue
        totals = expense_totals_by_statement.setdefault(
            entry["statement_id"], {currency: Decimal("0") for currency in CURRENCIES}
        )
        totals[entry["currency"]] += entry["amount"]

    result = []
    for statement in statements:
        expense_totals = expense_totals_by_statement.get(
            statement["id"], {currency: Decimal("0") for currency in CURRENCIES}
        )
        result.append({**statement, "status": statement_status(statement["period"]), "expense_totals": expense_totals})
    return result


def update_statement(
    card_id: str,
    statement_id: str,
    closing_date: str | None,
    due_date: str | None,
) -> None:
    statement = models.get_statement(statement_id, card_id)
    if statement is None:
        raise ValueError("statement not found")
    models.update_statement(statement_id, closing_date, due_date)


def get_statement_view(card_id: str, statement_id: str) -> dict:
    statement = models.get_statement(statement_id, card_id)
    if statement is None:
        return {"statement": None, "entries": [], "totals": {}}

    statement = {
        **statement,
        "start_date": _start_date_for(card_id, statement["period"]),
        "status": statement_status(statement["period"]),
    }
    all_entries = _entries_with_balance(card_id)
    statement_entries = [e for e in all_entries if e["statement_id"] == statement["id"]]

    totals = {}
    for currency in CURRENCIES:
        in_total = sum(
            (e["amount"] for e in statement_entries if e["currency"] == currency and e["entry_type"] == "payment"),
            Decimal("0"),
        )
        out_total = sum(
            (
                e["amount"]
                for e in statement_entries
                if e["currency"] == currency and e["entry_type"] in ("expense", "charge")
            ),
            Decimal("0"),
        )
        # Saldo acumulado hasta este resumen inclusive, no necesariamente el último
        # de la tarjeta: importa cuando se está mirando un resumen ya cerrado.
        balance = next(
            (
                e["balance_after"]
                for e in reversed(all_entries)
                if e["currency"] == currency and e["period"] <= statement["period"]
            ),
            Decimal("0"),
        )
        totals[currency] = {"in": in_total, "out": out_total, "balance": balance}

    return {"statement": statement, "entries": statement_entries, "totals": totals}
