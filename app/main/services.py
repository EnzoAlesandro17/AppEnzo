from dataclasses import dataclass, field
from datetime import date, timedelta

from app.agenda import services as agenda_services
from app.common.dates import WEEKDAYS_ES
from app.common.today import TodayItem
from app.tasks import services as tasks_services

MAX_ITEMS_PER_SECTION = 5


@dataclass(frozen=True)
class DayColumn:
    day: date
    label: str
    is_today: bool
    items: list[TodayItem] = field(default_factory=list)


@dataclass(frozen=True)
class DashboardView:
    today: date
    schedule_today: list[TodayItem]
    tasks_today: list[TodayItem]
    overdue: list[TodayItem]
    week_days: list[DayColumn]
    schedule_today_total: int
    tasks_today_total: int
    overdue_total: int


def _cap(items: list[TodayItem]) -> list[TodayItem]:
    return items[:MAX_ITEMS_PER_SECTION]


def _sort_key(item: TodayItem):
    # El estado laboral del día (trabajo/franco) va siempre primero: es el
    # dato más importante de la agenda, tenga hora o no.
    return (0 if item.kind == "work" else 1, item.time or "99:99", item.title)


def get_dashboard(user_id: str, today: date) -> DashboardView:
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    task_items = tasks_services.get_today_summary(user_id, today)
    agenda_items = agenda_services.get_today_summary(user_id, today)

    schedule_today = sorted(
        (item for item in agenda_items if item.item_date == today),
        key=_sort_key,
    )
    tasks_today = [item for item in task_items if item.item_date == today]
    overdue = [item for item in task_items if item.overdue]

    week_task_items = tasks_services.get_week_items(user_id, monday, sunday)
    week_agenda_items = agenda_services.get_week_items(user_id, monday, sunday)
    all_week_items = week_task_items + week_agenda_items

    week_days = []
    for offset in range(7):
        day = monday + timedelta(days=offset)
        day_items = sorted((item for item in all_week_items if item.item_date == day), key=_sort_key)
        week_days.append(
            DayColumn(
                day=day,
                label=f"{WEEKDAYS_ES[day.weekday()][:3]} {day.day}",
                is_today=day == today,
                items=day_items,
            )
        )

    return DashboardView(
        today=today,
        schedule_today=_cap(schedule_today),
        tasks_today=_cap(tasks_today),
        overdue=_cap(overdue),
        week_days=week_days,
        schedule_today_total=len(schedule_today),
        tasks_today_total=len(tasks_today),
        overdue_total=len(overdue),
    )
