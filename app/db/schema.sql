-- AppEnzo database schema (SQLite)
-- Convenciones: IDs de 12 caracteres alfanuméricos generados en la app
-- (app/common/ids.py), borrado lógico vía deleted_at en toda tabla de
-- datos de usuario. Fechas guardadas como TEXT ISO 'YYYY-MM-DD', horas como
-- TEXT 'HH:MM' 24hs (conversión a/desde date de Python explícita en cada
-- models.py). Este archivo representa la forma FINAL del schema — instala
-- una base nueva ya en esta forma. Una base existente se lleva hasta acá
-- mediante las migraciones versionadas en app/db/cli.py.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at    TEXT
);

-- Rubros de tareas configurables por el usuario (antes eran un CHECK fijo).
-- `key` es el valor guardado en tasks.context; `label` es lo que se muestra.
CREATE TABLE IF NOT EXISTS task_contexts (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users (id),
    key        TEXT NOT NULL,
    label      TEXT NOT NULL,
    position   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    UNIQUE (user_id, key)
);

CREATE TABLE IF NOT EXISTS tasks (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users (id),
    context      TEXT NOT NULL,  -- referencia lógica a task_contexts.key, validada en services.py
    title        TEXT NOT NULL,
    notes        TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'in_progress', 'blocked', 'done')),
    due_date     TEXT,  -- ISO 'YYYY-MM-DD', nullable (tareas sin fecha)
    due_time     TEXT,  -- 'HH:MM' 24hs, nullable (hora de inicio)
    end_time     TEXT,  -- 'HH:MM' 24hs, nullable (hora de fin)
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    deleted_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_status
    ON tasks (user_id, status) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_user_due
    ON tasks (user_id, due_date) WHERE deleted_at IS NULL AND due_date IS NOT NULL;

CREATE TABLE IF NOT EXISTS task_steps (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users (id),
    task_id    TEXT NOT NULL REFERENCES tasks (id),
    title      TEXT NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    position   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_task_steps_task
    ON task_steps (task_id) WHERE deleted_at IS NULL;

-- Agenda: 'work' unifica turno/franco (work_mode distingue cuál es), pagos
-- viven en Presupuesto (con due_date), 'medical'/'other' para el resto.
CREATE TABLE IF NOT EXISTS agenda_entries (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users (id),
    kind       TEXT NOT NULL CHECK (kind IN ('work', 'medical', 'other')),
    work_mode  TEXT CHECK (work_mode IN ('scheduled', 'off')),  -- solo aplica si kind='work'
    title      TEXT NOT NULL,
    notes      TEXT,
    entry_date TEXT NOT NULL,  -- ISO 'YYYY-MM-DD'
    entry_time TEXT,           -- 'HH:MM' 24hs, nullable (hora de inicio)
    end_time   TEXT,           -- 'HH:MM' 24hs, nullable (hora de fin)
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_agenda_user_date
    ON agenda_entries (user_id, entry_date) WHERE deleted_at IS NULL;

-- Presupuesto: cada gasto pertenece a un período (mes), puede tener
-- vencimiento propio, y puede ser repetitivo (series_id agrupa las
-- instancias mensuales de un mismo gasto recurrente, ej. alquiler).
CREATE TABLE IF NOT EXISTS budget_items (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users (id),
    period       TEXT NOT NULL,  -- ISO 'YYYY-MM-01', primer día del mes
    title        TEXT NOT NULL,
    amount       NUMERIC NOT NULL,
    due_date     TEXT,  -- ISO 'YYYY-MM-DD', nullable
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'paid', 'postponed')),
    is_recurring INTEGER NOT NULL DEFAULT 0 CHECK (is_recurring IN (0, 1)),
    series_id    TEXT,  -- agrupa instancias mensuales de un mismo gasto repetitivo
    notes        TEXT,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_budget_items_user_period
    ON budget_items (user_id, period) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_budget_items_series
    ON budget_items (series_id) WHERE deleted_at IS NULL AND series_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
