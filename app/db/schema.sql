-- AppEnzo database schema
-- Convenciones: IDs de 12 caracteres alfanuméricos generados en la app
-- (app/common/ids.py), borrado lógico vía deleted_at en toda tabla.

CREATE TYPE currency AS ENUM ('ARS', 'USD');
CREATE TYPE entry_type AS ENUM ('expense', 'payment', 'charge');

CREATE TABLE users (
    id            CHAR(12) PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ
);

CREATE TABLE cards (
    id               CHAR(12) PRIMARY KEY,
    user_id          CHAR(12) NOT NULL REFERENCES users (id),
    name             TEXT NOT NULL,
    bank             TEXT,
    last_four_digits CHAR(4),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX idx_cards_user_id ON cards (user_id) WHERE deleted_at IS NULL;

-- Un resumen por período de facturación de una tarjeta. `period` es el primer
-- día del mes que nombra al resumen (ej. 2026-07-01 = "resumen 2026-07"), y da
-- a la vez el orden y el nombre, sin depender de closing_date / due_date, que
-- el banco puede correr en cualquier momento. No hay start_date propio: el
-- inicio de un resumen es el día siguiente al cierre del resumen anterior
-- (period - 1 mes), se calcula en la app. No hay columna de "abierto/cerrado":
-- el estado se deriva comparando `period` contra el mes calendario actual.
CREATE TABLE statements (
    id           CHAR(12) PRIMARY KEY,
    card_id      CHAR(12) NOT NULL REFERENCES cards (id),
    period       DATE NOT NULL,
    closing_date DATE,
    due_date     DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ,
    UNIQUE (card_id, period)
);

CREATE INDEX idx_statements_card_id ON statements (card_id) WHERE deleted_at IS NULL;

-- Compra original dividida en N cuotas. Cada cuota resultante es una fila en
-- `entries`, encadenada a resúmenes consecutivos por período, no por fecha.
CREATE TABLE installment_plans (
    id                CHAR(12) PRIMARY KEY,
    card_id           CHAR(12) NOT NULL REFERENCES cards (id),
    currency          currency NOT NULL,
    total_amount      NUMERIC(14, 2) NOT NULL,
    installment_count SMALLINT NOT NULL CHECK (installment_count > 0),
    description       TEXT,
    purchase_date     DATE NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ
);

-- Gastos, pagos y cargos fijos (ej. impuesto al sello). Un cargo fijo se carga
-- directo a un statement_id puntual; su `date` es solo informativa.
CREATE TABLE entries (
    id                  CHAR(12) PRIMARY KEY,
    card_id             CHAR(12) NOT NULL REFERENCES cards (id),
    statement_id        CHAR(12) NOT NULL REFERENCES statements (id),
    installment_plan_id CHAR(12) REFERENCES installment_plans (id),
    installment_number  SMALLINT,
    entry_type          entry_type NOT NULL,
    currency            currency NOT NULL,
    amount              NUMERIC(14, 2) NOT NULL,
    description         TEXT,
    date                DATE NOT NULL,
    exchange_rate       NUMERIC(10, 4),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    CHECK (
        (installment_plan_id IS NULL AND installment_number IS NULL)
        OR (installment_plan_id IS NOT NULL AND installment_number IS NOT NULL)
    )
);

CREATE INDEX idx_entries_statement_id ON entries (statement_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_entries_card_id ON entries (card_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_entries_installment_plan_id ON entries (installment_plan_id) WHERE deleted_at IS NULL;
