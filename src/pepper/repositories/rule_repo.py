from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def add(conn: sqlite3.Connection, *, kind: str, target_type_id: int | None, param: str) -> int:
    cur = conn.execute(
        "INSERT INTO rules (kind, target_type_id, param, created_at) VALUES (?,?,?,?)",
        (kind, target_type_id, param, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return int(cur.lastrowid)


def by_kind(conn: sqlite3.Connection, kind: str) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM rules WHERE kind = ?", (kind,)).fetchall()
