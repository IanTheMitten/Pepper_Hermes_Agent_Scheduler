-- People referenced by schedule items (identity = id, never the name).
CREATE TABLE persons (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name       TEXT    NOT NULL,
    relationship       TEXT,
    counterparty_weight TEXT   NOT NULL DEFAULT 'none'
        CHECK (counterparty_weight IN ('none', 'low', 'high')),
    weight_source      TEXT    NOT NULL DEFAULT 'inferred'
        CHECK (weight_source IN ('user_set', 'learned', 'inferred')),
    created_at         TEXT    NOT NULL,
    updated_at         TEXT    NOT NULL
);

-- The live schedule. Columns beyond M1's use (scores, planner, recurrence) are
-- created now as nullable so later milestones add tables, not rewrite this one.
CREATE TABLE items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id           INTEGER,
    title             TEXT    NOT NULL,
    start_time        TEXT,
    end_time          TEXT,
    duration_estimate INTEGER,
    min_duration      INTEGER,
    location          TEXT,
    status            TEXT    NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'in_progress', 'done', 'dropped', 'cancelled')),
    commitment        TEXT    NOT NULL DEFAULT 'solo'
        CHECK (commitment IN ('solo', 'promise_to_self', 'promise_to_others')),
    counterparty_id   INTEGER REFERENCES persons(id),
    temporal_class    TEXT    NOT NULL DEFAULT 'anytime'
        CHECK (temporal_class IN ('fixed_time', 'deadline', 'anytime')),
    deadline          TEXT,
    stakes            TEXT    NOT NULL DEFAULT 'reschedulable'
        CHECK (stakes IN ('trivial_repeatable', 'reschedulable', 'one_shot')),
    divisibility      TEXT    NOT NULL DEFAULT 'atomic'
        CHECK (divisibility IN ('atomic', 'checkpointed', 'divisible')),
    rigidity_score    REAL,
    protection_score  REAL,
    goal_id           INTEGER,
    effort_estimate   INTEGER,
    project_id        INTEGER,
    auto_reserved     INTEGER NOT NULL DEFAULT 0,
    parent_item_id    INTEGER,
    series_id         INTEGER,
    detached          INTEGER NOT NULL DEFAULT 0,
    version           INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL
);

CREATE INDEX idx_items_start_time ON items(start_time);
