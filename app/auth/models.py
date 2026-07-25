from app.db.connection import transaction


def get_user_by_email(email: str) -> dict | None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash FROM users "
                "WHERE email = %s AND deleted_at IS NULL",
                (email,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "email": row[1], "password_hash": row[2]}


def get_user_by_id(user_id: str) -> dict | None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash FROM users "
                "WHERE id = %s AND deleted_at IS NULL",
                (user_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "email": row[1], "password_hash": row[2]}


def insert_user(user_id: str, email: str, password_hash: str) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                (user_id, email, password_hash),
            )
