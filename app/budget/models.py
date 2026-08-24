from datetime import date, datetime

from app.db.connection import transaction


def _row_to_item(row) -> dict:
    item = dict(row)
    item["period"] = datetime.strptime(item["period"], "%Y-%m-%d").date()
    if item["due_date"]:
        item["due_date"] = datetime.strptime(item["due_date"], "%Y-%m-%d").date()
    item["is_recurring"] = bool(item["is_recurring"])
    return item


def insert_item(
    item_id: str,
    user_id: str,
    period: date,
    title: str,
    amount: float,
    due_date: date | None,
    notes: str | None,
    is_recurring: bool,
    series_id: str | None,
) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO budget_items "
            "(id, user_id, period, title, amount, due_date, notes, is_recurring, series_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item_id,
                user_id,
                period.isoformat(),
                title,
                amount,
                due_date.isoformat() if due_date else None,
                notes,
                1 if is_recurring else 0,
                series_id,
            ),
        )


def list_period(user_id: str, period: date) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM budget_items "
            "WHERE user_id = ? AND period = ? AND deleted_at IS NULL "
            "ORDER BY created_at",
            (user_id, period.isoformat()),
        ).fetchall()
    return [_row_to_item(row) for row in rows]


def list_pending_before(user_id: str, period: date) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM budget_items "
            "WHERE user_id = ? AND deleted_at IS NULL AND status = 'pending' AND period < ? "
            "ORDER BY period, created_at",
            (user_id, period.isoformat()),
        ).fetchall()
    return [_row_to_item(row) for row in rows]


def list_latest_recurring_before(user_id: str, period: date) -> list[dict]:
    """Para cada serie de gastos repetitivos, la instancia más reciente
    anterior al período pedido — solo si esa última instancia sigue marcada
    como repetitiva (si el usuario la dio de baja, no aparece más)."""
    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT b.* FROM budget_items b
            JOIN (
                SELECT series_id, MAX(period) AS max_period
                FROM budget_items
                WHERE user_id = ? AND deleted_at IS NULL
                    AND series_id IS NOT NULL AND period < ?
                GROUP BY series_id
            ) latest ON b.series_id = latest.series_id AND b.period = latest.max_period
            WHERE b.user_id = ? AND b.deleted_at IS NULL AND b.is_recurring = 1
            """,
            (user_id, period.isoformat(), user_id),
        ).fetchall()
    return [_row_to_item(row) for row in rows]


def exists_for_series_period(user_id: str, series_id: str, period: date) -> bool:
    with transaction() as conn:
        row = conn.execute(
            "SELECT 1 FROM budget_items "
            "WHERE user_id = ? AND series_id = ? AND period = ? AND deleted_at IS NULL",
            (user_id, series_id, period.isoformat()),
        ).fetchone()
    return row is not None


def get_item(user_id: str, item_id: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM budget_items WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (item_id, user_id),
        ).fetchone()
    return _row_to_item(row) if row else None


def update_item(
    user_id: str,
    item_id: str,
    title: str,
    amount: float,
    due_date: date | None,
    notes: str | None,
    is_recurring: bool,
    series_id: str | None,
) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE budget_items SET title = ?, amount = ?, due_date = ?, notes = ?, "
            "is_recurring = ?, series_id = ? "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (
                title,
                amount,
                due_date.isoformat() if due_date else None,
                notes,
                1 if is_recurring else 0,
                series_id,
                item_id,
                user_id,
            ),
        )


def update_status(user_id: str, item_id: str, status: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE budget_items SET status = ? WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (status, item_id, user_id),
        )


def soft_delete(user_id: str, item_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE budget_items SET deleted_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (item_id, user_id),
        )
