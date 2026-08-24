from app.db.connection import transaction


def list_contexts(user_id: str) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM task_contexts WHERE user_id = ? AND deleted_at IS NULL "
            "ORDER BY position, created_at",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_label_map(user_id: str) -> dict[str, str]:
    """key -> label para TODOS los rubros del usuario, incluidos los
    archivados (para poder mostrar el nombre histórico de tareas viejas)."""
    with transaction() as conn:
        rows = conn.execute(
            "SELECT key, label FROM task_contexts WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def get_context_by_key(user_id: str, key: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM task_contexts WHERE user_id = ? AND key = ? AND deleted_at IS NULL",
            (user_id, key),
        ).fetchone()
    return dict(row) if row else None


def get_any_context_by_key(user_id: str, key: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM task_contexts WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()
    return dict(row) if row else None


def next_position(user_id: str) -> int:
    with transaction() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM task_contexts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row[0]


def insert_context(context_id: str, user_id: str, key: str, label: str, position: int) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO task_contexts (id, user_id, key, label, position) VALUES (?, ?, ?, ?, ?)",
            (context_id, user_id, key, label, position),
        )


def update_label(user_id: str, context_id: str, label: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE task_contexts SET label = ? WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (label, context_id, user_id),
        )


def soft_delete(user_id: str, context_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE task_contexts SET deleted_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (context_id, user_id),
        )


def count_tasks_using(user_id: str, key: str) -> int:
    with transaction() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND context = ? AND deleted_at IS NULL",
            (user_id, key),
        ).fetchone()
    return row[0]
