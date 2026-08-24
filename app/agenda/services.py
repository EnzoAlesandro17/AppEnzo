from collections import defaultdict
from datetime import date, timedelta

from app.agenda import models
from app.common.ids import generate_id
from app.common.today import TodayItem

KINDS = {
    "work": "Trabajo",
    "medical": "Turno médico",
    "other": "Otro",
}

WORK_MODES = {
    "scheduled": "Con horario",
    "off": "Libre",
}

WEEK_VIEW_DAYS = 14


class InvalidKind(Exception):
    pass


def create_entry(
    user_id: str,
    kind: str,
    title: str,
    notes: str | None,
    entry_date: date,
    entry_time: str | None = None,
    end_time: str | None = None,
    work_mode: str | None = None,
) -> str:
    if kind not in KINDS:
        raise InvalidKind(kind)

    title = title.strip()
    if kind == "work":
        work_mode = work_mode if work_mode in WORK_MODES else "scheduled"
        if work_mode == "off":
            entry_time, end_time = None, None
        if not title:
            title = "Franco" if work_mode == "off" else "Trabajo"
    else:
        work_mode = None
        if not title:
            title = KINDS[kind]

    entry_id = generate_id()
    models.insert_entry(entry_id, user_id, kind, work_mode, title, notes, entry_date, entry_time, end_time)
    return entry_id


def list_week(user_id: str, start_date: date) -> dict[date, list[dict]]:
    end_date = start_date + timedelta(days=WEEK_VIEW_DAYS - 1)
    rows = models.list_range(user_id, start_date, end_date)
    grouped: dict[date, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["entry_date"]].append(row)
    return dict(grouped)


def delete_entry(user_id: str, entry_id: str) -> None:
    models.soft_delete(user_id, entry_id)


def kind_label(row: dict) -> str:
    if row["kind"] == "work" and row["work_mode"] == "off":
        return "Franco"
    return KINDS[row["kind"]]


def _row_to_item(row: dict) -> TodayItem:
    return TodayItem(
        item_date=row["entry_date"],
        time=row["entry_time"],
        end_time=row["end_time"],
        title=row["title"],
        subtitle=kind_label(row),
        kind=row["kind"],
        overdue=False,
        url="/agenda",
    )


def get_today_summary(user_id: str, today: date) -> list[TodayItem]:
    """Eventos de agenda de hoy y del resto de la semana calendario."""
    end_of_week = today + timedelta(days=6 - today.weekday())
    rows = models.list_range(user_id, today, end_of_week)
    return [_row_to_item(row) for row in rows]


def get_week_items(user_id: str, start_date: date, end_date: date) -> list[TodayItem]:
    rows = models.list_range(user_id, start_date, end_date)
    return [_row_to_item(row) for row in rows]
