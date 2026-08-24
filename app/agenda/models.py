from datetime import date, datetime

from app.db.connection import transaction


def _row_to_entry(row) -> dict:
    entry = dict(row)
    entry["entry_date"] = datetime.strptime(entry["entry_date"], "%Y-%m-%d").date()
    return entry


def insert_entry(
    entry_id: str,
    user_id: str,
    kind: str,
    work_mode: str | None,
    title: str,
    notes: str | None,
    entry_date: date,
    entry_time: str | None,
    end_time: str | None,
) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO agenda_entries "
            "(id, user_id, kind, work_mode, title, notes, entry_date, entry_time, end_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_id, user_id, kind, work_mode, title, notes, entry_date.isoformat(), entry_time, end_time),
        )


def list_range(user_id: str, start_date: date, end_date: date) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM agenda_entries "
            "WHERE user_id = ? AND deleted_at IS NULL "
            "AND entry_date >= ? AND entry_date <= ? "
            "ORDER BY entry_date, entry_time IS NULL, entry_time",
            (user_id, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return [_row_to_entry(row) for row in rows]


def soft_delete(user_id: str, entry_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE agenda_entries SET deleted_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (entry_id, user_id),
        )
