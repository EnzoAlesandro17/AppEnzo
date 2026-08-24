import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(os.environ["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
