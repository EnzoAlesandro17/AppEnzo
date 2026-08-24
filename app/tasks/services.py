from datetime import date, datetime, timedelta

from app.common.ids import generate_id
from app.common.today import TodayItem
from app.settings import services as settings_services
from app.tasks import models

STATUSES = {
    "pending": "Pendiente",
    "in_progress": "En progreso",
    "blocked": "Bloqueada",
    "done": "Hecha",
}


class InvalidContext(Exception):
    pass


class InvalidStatus(Exception):
    pass


class TaskNotFound(Exception):
    pass


def create_task(
    user_id: str,
    context: str,
    title: str,
    notes: str | None,
    due_date: date | None,
    due_time: str | None = None,
    end_time: str | None = None,
) -> str:
    if settings_services.get_context(user_id, context) is None:
        raise InvalidContext(context)
    task_id = generate_id()
    models.insert_task(task_id, user_id, context, title, notes, due_date, due_time, end_time)
    return task_id


def list_grouped(user_id: str) -> dict[str, dict]:
    """{context_key: {"label": str, "tasks": [...]}} en el orden configurado
    en Configuración. Incluye tareas hechas (se muestran tachadas, no
    desaparecen). Si una tarea quedó con un rubro que ya fue borrado, se
    agrupa aparte marcada como archivada, para no perderla de vista."""
    contexts = settings_services.list_contexts(user_id)
    all_labels = settings_services.get_label_map(user_id)
    tasks = models.list_tasks(user_id)

    grouped: dict[str, dict] = {c["key"]: {"label": c["label"], "tasks": []} for c in contexts}
    for task in tasks:
        key = task["context"]
        if key not in grouped:
            label = all_labels.get(key, key)
            grouped[key] = {"label": f"{label} (archivado)", "tasks": []}
        grouped[key]["tasks"].append(task)
    return grouped


def set_status(user_id: str, task_id: str, status: str) -> None:
    if status not in STATUSES:
        raise InvalidStatus(status)
    completed_at = datetime.now().isoformat() if status == "done" else None
    models.update_status(user_id, task_id, status, completed_at)


def delete_task(user_id: str, task_id: str) -> None:
    models.soft_delete(user_id, task_id)


def get_today_summary(user_id: str, today: date) -> list[TodayItem]:
    """Tareas relevantes para el dashboard: vencidas y las que vencen hasta
    el domingo de esta semana, sin contar las ya hechas."""
    label_map = settings_services.get_label_map(user_id)
    end_of_week = today + timedelta(days=6 - today.weekday())
    rows = models.list_relevant_for_dashboard(user_id, end_of_week)
    return [_row_to_item(row, today, label_map) for row in rows]


def get_week_items(user_id: str, start_date: date, end_date: date) -> list[TodayItem]:
    """Todas las tareas con fecha dentro de la semana (incluye hechas, para
    poder visualizar la semana completa en la portada)."""
    label_map = settings_services.get_label_map(user_id)
    rows = models.list_for_week(user_id, start_date, end_date)
    return [_row_to_item(row, start_date, label_map, ignore_overdue=True) for row in rows]


def _row_to_item(row: dict, today: date, label_map: dict[str, str], ignore_overdue: bool = False) -> TodayItem:
    return TodayItem(
        item_date=row["due_date"],
        time=row["due_time"],
        end_time=row["end_time"],
        title=row["title"],
        subtitle=label_map.get(row["context"], row["context"]),
        kind="task",
        overdue=(not ignore_overdue) and row["due_date"] < today and row["status"] != "done",
        url="/tasks",
        done=row["status"] == "done",
    )


def get_task_detail(user_id: str, task_id: str) -> dict | None:
    task = models.get_task(user_id, task_id)
    if task is None:
        return None
    task["steps"] = models.list_steps(user_id, task_id)
    return task


def add_step(user_id: str, task_id: str, title: str) -> str:
    if models.get_task(user_id, task_id) is None:
        raise TaskNotFound(task_id)
    position = len(models.list_steps(user_id, task_id))
    step_id = generate_id()
    models.insert_step(step_id, user_id, task_id, title, position)
    return step_id


def toggle_step(user_id: str, step_id: str, done: bool) -> None:
    models.update_step_done(user_id, step_id, done)


def delete_step(user_id: str, step_id: str) -> None:
    models.soft_delete_step(user_id, step_id)
