from app.db.connection import transaction

STATEMENT_COLUMNS = ["id", "card_id", "period", "closing_date", "due_date"]
STATEMENT_SELECT = "SELECT id, card_id, period, closing_date, due_date FROM statements"


def create_card(card_id: str, user_id: str, name: str, bank: str | None, last_four_digits: str | None) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO cards (id, user_id, name, bank, last_four_digits) "
                "VALUES (%s, %s, %s, %s, %s)",
                (card_id, user_id, name, bank, last_four_digits),
            )


def list_cards(user_id: str) -> list[dict]:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, bank, last_four_digits FROM cards "
                "WHERE user_id = %s AND deleted_at IS NULL ORDER BY name",
                (user_id,),
            )
            rows = cur.fetchall()
    columns = ["id", "name", "bank", "last_four_digits"]
    return [dict(zip(columns, row)) for row in rows]


def get_card(card_id: str, user_id: str) -> dict | None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, bank, last_four_digits FROM cards "
                "WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (card_id, user_id),
            )
            row = cur.fetchone()
    if row is None:
        return None
    columns = ["id", "name", "bank", "last_four_digits"]
    return dict(zip(columns, row))


def insert_statement(statement_id: str, card_id: str, period) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO statements (id, card_id, period) VALUES (%s, %s, %s)",
                (statement_id, card_id, period),
            )


def get_statement_by_period(card_id: str, period) -> dict | None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"{STATEMENT_SELECT} WHERE card_id = %s AND period = %s AND deleted_at IS NULL",
                (card_id, period),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return dict(zip(STATEMENT_COLUMNS, row))


def get_statement(statement_id: str, card_id: str) -> dict | None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"{STATEMENT_SELECT} WHERE id = %s AND card_id = %s AND deleted_at IS NULL",
                (statement_id, card_id),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return dict(zip(STATEMENT_COLUMNS, row))


def list_statements(card_id: str) -> list[dict]:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"{STATEMENT_SELECT} WHERE card_id = %s AND deleted_at IS NULL ORDER BY period DESC",
                (card_id,),
            )
            rows = cur.fetchall()
    return [dict(zip(STATEMENT_COLUMNS, row)) for row in rows]


def update_statement(statement_id: str, closing_date: str | None, due_date: str | None) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE statements SET closing_date = %s, due_date = %s WHERE id = %s",
                (closing_date, due_date, statement_id),
            )


def soft_delete_statement(statement_id: str) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE statements SET deleted_at = now() WHERE id = %s", (statement_id,))


def count_entries_for_statement(statement_id: str) -> int:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM entries WHERE statement_id = %s AND deleted_at IS NULL",
                (statement_id,),
            )
            (count,) = cur.fetchone()
    return count


def insert_installment_plan(
    plan_id: str,
    card_id: str,
    currency: str,
    total_amount,
    installment_count: int,
    description: str | None,
    purchase_date: str,
) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO installment_plans "
                "(id, card_id, currency, total_amount, installment_count, description, purchase_date) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (plan_id, card_id, currency, total_amount, installment_count, description, purchase_date),
            )


def insert_entry(
    entry_id: str,
    card_id: str,
    statement_id: str,
    entry_type: str,
    currency: str,
    amount,
    description: str | None,
    date: str,
    installment_plan_id: str | None = None,
    installment_number: int | None = None,
) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO entries "
                "(id, card_id, statement_id, installment_plan_id, installment_number, "
                " entry_type, currency, amount, description, date) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    entry_id,
                    card_id,
                    statement_id,
                    installment_plan_id,
                    installment_number,
                    entry_type,
                    currency,
                    amount,
                    description,
                    date,
                ),
            )


def get_entry(entry_id: str, card_id: str) -> dict | None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, statement_id FROM entries "
                "WHERE id = %s AND card_id = %s AND deleted_at IS NULL",
                (entry_id, card_id),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "statement_id": row[1]}


def soft_delete_entry(entry_id: str) -> None:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE entries SET deleted_at = now() WHERE id = %s", (entry_id,))


def list_entries_for_card(card_id: str) -> list[dict]:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT e.id, e.date, e.entry_type, e.currency, e.amount, e.description, "
                "       e.installment_number, s.period, s.id AS statement_id "
                "FROM entries e "
                "JOIN statements s ON s.id = e.statement_id "
                "WHERE e.card_id = %s AND e.deleted_at IS NULL AND s.deleted_at IS NULL "
                "ORDER BY s.period, e.date, e.created_at",
                (card_id,),
            )
            rows = cur.fetchall()
    columns = [
        "id", "date", "entry_type", "currency", "amount", "description",
        "installment_number", "period", "statement_id",
    ]
    return [dict(zip(columns, row)) for row in rows]
