-- Stable activity buckets. items.type_id (from M1) references these.
CREATE TABLE types (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

-- Embedding index: one row per remembered title, linked to a type.
CREATE TABLE vectors (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id            INTEGER NOT NULL REFERENCES types(id),
    embedding          BLOB    NOT NULL,   -- float32 array bytes
    confidence         REAL    NOT NULL DEFAULT 0.5,
    last_reinforced_at TEXT    NOT NULL,
    created_at         TEXT    NOT NULL
);

CREATE INDEX idx_vectors_type ON vectors(type_id);
