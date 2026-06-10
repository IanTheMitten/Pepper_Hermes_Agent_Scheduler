-- Layer 1: immutable diary of what actually happened.
CREATE TABLE observations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id        INTEGER REFERENCES types(id),
    item_id        INTEGER,
    estimated      INTEGER,
    actual         INTEGER,
    scheduled_start TEXT,
    actual_start   TEXT,
    start_slip     INTEGER,
    scope_reached  REAL,
    outcome        TEXT NOT NULL
        CHECK (outcome IN ('done', 'partial', 'dropped_pressure', 'dropped_user')),
    day_of_week    INTEGER,
    time_of_day    TEXT,
    location       TEXT,
    preceded_by    INTEGER,
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_obs_type ON observations(type_id);

-- Layer 2: derived per-type predictions (recomputed from observations).
CREATE TABLE type_stats (
    type_id            INTEGER PRIMARY KEY REFERENCES types(id),
    avg_actual         REAL,
    overrun            REAL,
    avg_start_slip     REAL,
    spread             REAL,
    sample_count       INTEGER NOT NULL DEFAULT 0,
    confidence         REAL    NOT NULL DEFAULT 0.0,
    typical_buffer     REAL,
    time_per_scope_unit REAL,
    drop_tendency      REAL,
    updated_at         TEXT
);

-- Personal-bias profile: factor-keyed bounded/damped corrections.
CREATE TABLE user_bias (
    axis         TEXT NOT NULL,   -- social | character | stakes | time_of_day
    value        TEXT NOT NULL,
    bias_factor  REAL NOT NULL DEFAULT 1.0,
    sample_count INTEGER NOT NULL DEFAULT 0,
    confidence   REAL NOT NULL DEFAULT 0.0,
    updated_at   TEXT,
    PRIMARY KEY (axis, value)
);
