from app.db.connection import transaction


def get_user_by_email(email: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users "
            "WHERE email = ? AND deleted_at IS NULL",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users "
            "WHERE id = ? AND deleted_at IS NULL",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def insert_user(user_id: str, email: str, password_hash: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (user_id, email, password_hash),
        )
