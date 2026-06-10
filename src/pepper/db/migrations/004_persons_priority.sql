CREATE TABLE person_aliases (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES persons(id),
    alias     TEXT NOT NULL,
    UNIQUE (person_id, alias)
);
CREATE INDEX idx_alias_name ON person_aliases(alias);

CREATE TABLE person_context (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id    INTEGER NOT NULL REFERENCES persons(id),
    signal_type  TEXT NOT NULL,   -- activity | location | co_mention | role
    signal_value TEXT NOT NULL,
    count        INTEGER NOT NULL DEFAULT 1,
    UNIQUE (person_id, signal_type, signal_value)
);
