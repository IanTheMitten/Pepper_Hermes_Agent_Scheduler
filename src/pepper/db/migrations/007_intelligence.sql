CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER REFERENCES items(id),
    remind_at TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('telegram', 'app_push')),
    sent_at TEXT, response TEXT, response_at TEXT,
    lead_override INTEGER
);

CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,            -- no_before | cost_bias
    target_type_id INTEGER,        -- null = applies to all
    param TEXT,                    -- 'HH:MM' for no_before; numeric factor for cost_bias
    created_at TEXT NOT NULL
);

CREATE TABLE objectives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    target_type_id INTEGER,        -- null = global
    weight REAL NOT NULL DEFAULT 1.1,
    until TEXT, active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
