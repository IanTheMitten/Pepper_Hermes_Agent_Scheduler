from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def create(conn: sqlite3.Connection, description: str, *, target_type_id: int | None,
           weight: float = 1.1, until: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO objectives (description, target_type_id, weight, until, active, created_at) "
        "VALUES (?,?,?,?,1,?)",
        (description, target_type_id, weight, until, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return int(cur.lastrowid)


def active(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM objectives WHERE active = 1").fetchall()


def deactivate(conn: sqlite3.Connection, objective_id: int) -> None:
    conn.execute("UPDATE objectives SET active = 0 WHERE id = ?", (objective_id,))
    conn.commit()
