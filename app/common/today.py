from dataclasses import dataclass
from datetime import date

# kind: "task" (Tareas) | "shift" | "day_off" | "payment" | "medical" | "other" (Agenda)


@dataclass(frozen=True)
class TodayItem:
    item_date: date
    time: str | None  # "HH:MM" de inicio, nullable
    title: str
    subtitle: str | None  # contexto de la tarea o etiqueta del tipo de evento
    kind: str
    overdue: bool  # True solo para tareas con due_date < hoy y status != 'done'
    url: str  # "/tasks" o "/agenda"
    end_time: str | None = None  # "HH:MM" de fin, nullable
    done: bool = False  # True para tareas ya hechas (usado en la vista semanal)


def time_range_label(item: TodayItem) -> str:
    if not item.time:
        return ""
    if item.end_time:
        return f"{item.time}–{item.end_time}"
    return item.time


def badge_class(item: TodayItem) -> str:
    if item.overdue:
        return "badge-error"
    if item.kind == "task":
        return "badge-info"
    if item.kind == "work":
        return "badge-primary"
    return "badge-warning"  # medical, other
