CREATE TABLE travel (
    loc_a      TEXT NOT NULL,
    loc_b      TEXT NOT NULL,
    minutes    INTEGER NOT NULL,
    source     TEXT NOT NULL DEFAULT 'manual'   -- learned | manual | api
        CHECK (source IN ('learned', 'manual', 'api')),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (loc_a, loc_b)
);

CREATE TABLE conflicts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    item_a_id        INTEGER,
    item_b_id        INTEGER,
    resolution_method TEXT,   -- auto | user
    lever_used       TEXT,    -- absorb | compress | shift | reorder | split | drop
    resolved_at      TEXT NOT NULL
);
