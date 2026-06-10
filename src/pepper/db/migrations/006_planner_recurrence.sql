CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, deadline TEXT, status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER REFERENCES items(id),
    description TEXT,
    granularity TEXT NOT NULL DEFAULT 'coarse' CHECK (granularity IN ('coarse', 'checkpointed')),
    total_scope REAL, scope_done REAL NOT NULL DEFAULT 0,
    source TEXT, doc_ref TEXT, updated_at TEXT
);

CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL REFERENCES goals(id),
    label TEXT, done INTEGER NOT NULL DEFAULT 0,
    est_duration INTEGER, actual_duration INTEGER
);

CREATE TABLE recurrence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, type_id INTEGER,
    freq TEXT NOT NULL CHECK (freq IN ('daily', 'weekly', 'monthly')),
    interval INTEGER NOT NULL DEFAULT 1,
    byday TEXT, at_time TEXT NOT NULL, duration_estimate INTEGER NOT NULL,
    until TEXT, location TEXT,
    commitment TEXT NOT NULL DEFAULT 'solo',
    counterparty_id INTEGER, temporal_class TEXT NOT NULL DEFAULT 'fixed_time',
    stakes TEXT NOT NULL DEFAULT 'reschedulable',
    divisibility TEXT NOT NULL DEFAULT 'atomic',
    materialized_through TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
