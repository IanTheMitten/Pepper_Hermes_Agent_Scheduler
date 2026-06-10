from __future__ import annotations

import sqlite3
from pathlib import Path

from pepper import config


def get_connection(path: str | Path | None = None) -> sqlite3.Connection:
    target = Path(path) if path is not None else config.db_path()
    if str(target) != ":memory:":
        target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
