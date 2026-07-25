import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


def get_connection() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


@contextmanager
def transaction() -> Iterator[psycopg.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
