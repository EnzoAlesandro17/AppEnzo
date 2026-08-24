import os
import sqlite3
from pathlib import Path

import click

from app.common.ids import generate_id

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DEFAULT_CONTEXTS = [
    ("home", "Casa"),
    ("work", "Trabajo"),
    ("shopping", "Compras"),
    ("projects", "Proyectos"),
]


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def _migration_1_task_times(conn: sqlite3.Connection) -> None:
    """Agrega hora de inicio/fin a tareas, y hora de fin a agenda."""
    _add_column_if_missing(conn, "tasks", "due_time", "TEXT")
    _add_column_if_missing(conn, "tasks", "end_time", "TEXT")
    _add_column_if_missing(conn, "agenda_entries", "end_time", "TEXT")


def _migration_2_configurable_contexts(conn: sqlite3.Connection) -> None:
    """Rubros de tareas configurables: crea task_contexts (sembrando los 4
    rubros históricos para cada usuario existente) y reconstruye tasks sin
    el CHECK fijo de context."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_contexts (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users (id),
            key        TEXT NOT NULL,
            label      TEXT NOT NULL,
            position   INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            UNIQUE (user_id, key)
        )
        """
    )
    for (user_id,) in conn.execute("SELECT id FROM users"):
        existing = {
            row[0]
            for row in conn.execute("SELECT key FROM task_contexts WHERE user_id = ?", (user_id,))
        }
        for position, (key, label) in enumerate(DEFAULT_CONTEXTS):
            if key not in existing:
                conn.execute(
                    "INSERT INTO task_contexts (id, user_id, key, label, position) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (generate_id(), user_id, key, label, position),
                )

    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "id" not in columns:
        return  # tabla nueva ya sin CHECK, nada que migrar

    create_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"
    ).fetchone()[0]
    if "CHECK (context IN" not in create_sql:
        return  # ya migrada

    conn.execute("ALTER TABLE tasks RENAME TO tasks_old")
    conn.execute(
        """
        CREATE TABLE tasks (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL REFERENCES users (id),
            context      TEXT NOT NULL,
            title        TEXT NOT NULL,
            notes        TEXT,
            status       TEXT NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'in_progress', 'blocked', 'done')),
            due_date     TEXT,
            due_time     TEXT,
            end_time     TEXT,
            created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            deleted_at   TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO tasks (id, user_id, context, title, notes, status, due_date, "
        "due_time, end_time, created_at, completed_at, deleted_at) "
        "SELECT id, user_id, context, title, notes, status, due_date, "
        "due_time, end_time, created_at, completed_at, deleted_at FROM tasks_old"
    )
    conn.execute("DROP TABLE tasks_old")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_status "
        "ON tasks (user_id, status) WHERE deleted_at IS NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_due "
        "ON tasks (user_id, due_date) WHERE deleted_at IS NULL AND due_date IS NOT NULL"
    )


def _migration_3_agenda_work_kind(conn: sqlite3.Connection) -> None:
    """Unifica 'shift'/'day_off' en un único kind 'work' (+ work_mode
    scheduled/off); 'payment' pasa a 'other' (los pagos ahora viven en
    Presupuesto, con su propio due_date)."""
    create_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='agenda_entries'"
    ).fetchone()[0]
    if "'work'" in create_sql and "work_mode" in create_sql:
        return  # ya migrada

    conn.execute("ALTER TABLE agenda_entries RENAME TO agenda_entries_old")
    conn.execute(
        """
        CREATE TABLE agenda_entries (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users (id),
            kind       TEXT NOT NULL CHECK (kind IN ('work', 'medical', 'other')),
            work_mode  TEXT CHECK (work_mode IN ('scheduled', 'off')),
            title      TEXT NOT NULL,
            notes      TEXT,
            entry_date TEXT NOT NULL,
            entry_time TEXT,
            end_time   TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
        """
    )
    rows = conn.execute(
        "SELECT id, user_id, kind, title, notes, entry_date, entry_time, end_time, "
        "created_at, deleted_at FROM agenda_entries_old"
    ).fetchall()
    for (id_, user_id, kind, title, notes, entry_date, entry_time, end_time, created_at, deleted_at) in rows:
        if kind == "shift":
            new_kind, work_mode = "work", "scheduled"
        elif kind == "day_off":
            new_kind, work_mode = "work", "off"
            entry_time, end_time = None, None
        elif kind == "payment":
            new_kind, work_mode = "other", None
        else:
            new_kind, work_mode = kind, None
        conn.execute(
            "INSERT INTO agenda_entries (id, user_id, kind, work_mode, title, notes, "
            "entry_date, entry_time, end_time, created_at, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (id_, user_id, new_kind, work_mode, title, notes, entry_date, entry_time,
             end_time, created_at, deleted_at),
        )
    conn.execute("DROP TABLE agenda_entries_old")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agenda_user_date "
        "ON agenda_entries (user_id, entry_date) WHERE deleted_at IS NULL"
    )


def _migration_4_budget_due_and_recurring(conn: sqlite3.Connection) -> None:
    """Vencimiento propio y gastos repetitivos en Presupuesto."""
    _add_column_if_missing(conn, "budget_items", "due_date", "TEXT")
    _add_column_if_missing(conn, "budget_items", "is_recurring", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "budget_items", "series_id", "TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_budget_items_series "
        "ON budget_items (series_id) WHERE deleted_at IS NULL AND series_id IS NOT NULL"
    )


def _migration_5_fix_task_steps_fk(conn: sqlite3.Connection) -> None:
    """La reconstrucción de `tasks` en la migración 2 dejó a task_steps con
    un FK colgando de "tasks_old" (SQLite reescribe automáticamente las
    referencias de otras tablas al hacer RENAME, y esa tabla temporal
    después se borra). La reconstruye apuntando a "tasks" correctamente."""
    create_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='task_steps'"
    ).fetchone()[0]
    if "tasks_old" not in create_sql:
        return  # ya está bien

    conn.execute("ALTER TABLE task_steps RENAME TO task_steps_old")
    conn.execute(
        """
        CREATE TABLE task_steps (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users (id),
            task_id    TEXT NOT NULL REFERENCES tasks (id),
            title      TEXT NOT NULL,
            done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
            position   INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO task_steps (id, user_id, task_id, title, done, position, created_at, deleted_at) "
        "SELECT id, user_id, task_id, title, done, position, created_at, deleted_at FROM task_steps_old"
    )
    conn.execute("DROP TABLE task_steps_old")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_steps_task "
        "ON task_steps (task_id) WHERE deleted_at IS NULL"
    )


MIGRATIONS = [
    (1, _migration_1_task_times),
    (2, _migration_2_configurable_contexts),
    (3, _migration_3_agenda_work_kind),
    (4, _migration_4_budget_due_and_recurring),
    (5, _migration_5_fix_task_steps_fk),
]
LATEST_VERSION = MIGRATIONS[-1][0]


def _get_version(conn: sqlite3.Connection) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT)")
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
    return int(row[0]) if row else 0


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(version),),
    )


@click.command("init-db")
def init_db_command() -> None:
    # Conexión propia (no la de app.db.connection.transaction): algunas
    # migraciones reconstruyen tablas referenciadas por FK de otras tablas
    # (ej. tasks <- task_steps), y SQLite exige foreign_keys=OFF *antes* de
    # que arranque cualquier transacción para poder hacerlo — no se puede
    # activar/desactivar a mitad de una. Se reactiva al final.
    conn = sqlite3.connect(os.environ["DATABASE_PATH"])
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        existing_tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        is_fresh_install = "tasks" not in existing_tables

        if not is_fresh_install:
            # Las migraciones traen las tablas existentes a la forma que
            # schema.sql da por sentada (columnas nuevas, etc.) ANTES de
            # correrlo, porque schema.sql solo sabe crear desde cero
            # (CREATE TABLE/INDEX IF NOT EXISTS no agrega columnas a algo
            # que ya existe).
            current = _get_version(conn)
            for version, migrate in MIGRATIONS:
                if current < version:
                    migrate(conn)
                    _set_version(conn, version)
                    current = version

        conn.executescript(SCHEMA_PATH.read_text())

        if is_fresh_install:
            _set_version(conn, LATEST_VERSION)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
    click.echo("Base de datos inicializada.")
    _ensure_admin_from_env()


def _ensure_admin_from_env() -> None:
    """Crea el usuario inicial a partir de ADMIN_EMAIL/ADMIN_PASSWORD si
    están definidas y ese email todavía no existe. Pensado para hosts sin
    shell interactivo (ej. Render free), donde `flask create-user` — que
    pide la contraseña por prompt — no se puede correr. No hace nada si las
    variables no están seteadas, o si el usuario ya existe."""
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        return

    from app.auth import services as auth_services

    try:
        auth_services.create_user(email, password)
        click.echo(f"Usuario inicial creado: {email}")
    except auth_services.EmailAlreadyRegistered:
        pass
