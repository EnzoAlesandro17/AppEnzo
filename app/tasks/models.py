from datetime import date, datetime

from app.db.connection import transaction


def _row_to_task(row) -> dict:
    task = dict(row)
    if task["due_date"]:
        task["due_date"] = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
    return task


def insert_task(
    task_id: str,
    user_id: str,
    context: str,
    title: str,
    notes: str | None,
    due_date: date | None,
    due_time: str | None,
    end_time: str | None,
) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO tasks (id, user_id, context, title, notes, due_date, due_time, end_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                user_id,
                context,
                title,
                notes,
                due_date.isoformat() if due_date else None,
                due_time,
                end_time,
            ),
        )


def list_tasks(user_id: str) -> list[dict]:
    """Todas las tareas no borradas, hechas incluidas (se muestran tachadas
    en la UI hasta que el usuario decide borrarlas)."""
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks "
            "WHERE user_id = ? AND deleted_at IS NULL "
            "ORDER BY status = 'done', due_date IS NULL, due_date, "
            "due_time IS NULL, due_time, created_at",
            (user_id,),
        ).fetchall()
    return [_row_to_task(row) for row in rows]


def list_relevant_for_dashboard(user_id: str, end_date: date) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks "
            "WHERE user_id = ? AND deleted_at IS NULL AND status != 'done' "
            "AND due_date IS NOT NULL AND due_date <= ? "
            "ORDER BY due_date, due_time IS NULL, due_time",
            (user_id, end_date.isoformat()),
        ).fetchall()
    return [_row_to_task(row) for row in rows]


def list_for_week(user_id: str, start_date: date, end_date: date) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks "
            "WHERE user_id = ? AND deleted_at IS NULL "
            "AND due_date IS NOT NULL AND due_date >= ? AND due_date <= ? "
            "ORDER BY due_date, due_time IS NULL, due_time",
            (user_id, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return [_row_to_task(row) for row in rows]


def get_task(user_id: str, task_id: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (task_id, user_id),
        ).fetchone()
    return _row_to_task(row) if row else None


def update_status(user_id: str, task_id: str, status: str, completed_at: str | None) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ? "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (status, completed_at, task_id, user_id),
        )


def soft_delete(user_id: str, task_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE tasks SET deleted_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (task_id, user_id),
        )


# ---- Checklist / etapas de una tarea ----


def list_steps(user_id: str, task_id: str) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM task_steps "
            "WHERE task_id = ? AND user_id = ? AND deleted_at IS NULL "
            "ORDER BY position, created_at",
            (task_id, user_id),
        ).fetchall()
    return [dict(row) for row in rows]


def insert_step(step_id: str, user_id: str, task_id: str, title: str, position: int) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO task_steps (id, user_id, task_id, title, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, user_id, task_id, title, position),
        )


def update_step_done(user_id: str, step_id: str, done: bool) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE task_steps SET done = ? WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (1 if done else 0, step_id, user_id),
        )


def soft_delete_step(user_id: str, step_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE task_steps SET deleted_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (step_id, user_id),
        )
