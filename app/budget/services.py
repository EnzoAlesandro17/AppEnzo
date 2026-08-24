from dataclasses import dataclass
from datetime import date

from app.budget import models
from app.common.ids import generate_id

STATUSES = {
    "pending": "Pendiente",
    "paid": "Pagado",
    "postponed": "Aplazado",
}


class InvalidStatus(Exception):
    pass


class ItemNotFound(Exception):
    pass


@dataclass(frozen=True)
class BudgetView:
    period: date
    native_items: list[dict]
    rollover_items: list[dict]
    total: float
    subtotal: float


def _first_of_month(value: date) -> date:
    return value.replace(day=1)


def create_item(
    user_id: str,
    period: date,
    title: str,
    amount: float,
    due_date: date | None,
    notes: str | None,
    is_recurring: bool,
) -> str:
    item_id = generate_id()
    series_id = generate_id() if is_recurring else None
    models.insert_item(
        item_id, user_id, _first_of_month(period), title, amount, due_date, notes, is_recurring, series_id
    )
    return item_id


def _materialize_recurring(user_id: str, period: date) -> None:
    """Genera, si hace falta, la instancia de este mes para cada gasto
    repetitivo activo, heredando el monto de la última instancia (a menos
    que el usuario ya haya cargado algo para este mes)."""
    for candidate in models.list_latest_recurring_before(user_id, period):
        if not models.exists_for_series_period(user_id, candidate["series_id"], period):
            models.insert_item(
                generate_id(),
                user_id,
                period,
                candidate["title"],
                candidate["amount"],
                None,
                candidate["notes"],
                True,
                candidate["series_id"],
            )


def get_period_view(user_id: str, period: date) -> BudgetView:
    period = _first_of_month(period)
    _materialize_recurring(user_id, period)
    native_items = models.list_period(user_id, period)
    rollover_items = models.list_pending_before(user_id, period)
    total = sum(item["amount"] for item in native_items)
    subtotal = sum(
        item["amount"] for item in native_items + rollover_items if item["status"] == "pending"
    )
    return BudgetView(
        period=period,
        native_items=native_items,
        rollover_items=rollover_items,
        total=total,
        subtotal=subtotal,
    )


def get_item(user_id: str, item_id: str) -> dict | None:
    return models.get_item(user_id, item_id)


def update_item(
    user_id: str,
    item_id: str,
    title: str,
    amount: float,
    due_date: date | None,
    notes: str | None,
    is_recurring: bool,
) -> None:
    existing = models.get_item(user_id, item_id)
    if existing is None:
        raise ItemNotFound(item_id)
    series_id = existing["series_id"]
    if is_recurring and not series_id:
        series_id = generate_id()
    models.update_item(user_id, item_id, title, amount, due_date, notes, is_recurring, series_id)


def set_status(user_id: str, item_id: str, status: str) -> None:
    if status not in STATUSES:
        raise InvalidStatus(status)
    models.update_status(user_id, item_id, status)


def delete_item(user_id: str, item_id: str) -> None:
    models.soft_delete(user_id, item_id)
