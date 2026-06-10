from __future__ import annotations

import sqlite3


def add(conn: sqlite3.Connection, *, item_id: int, remind_at: str, channel: str,
        lead_override: int | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO reminders (item_id, remind_at, channel, lead_override) VALUES (?,?,?,?)",
        (item_id, remind_at, channel, lead_override),
    )
    conn.commit()
    return int(cur.lastrowid)
