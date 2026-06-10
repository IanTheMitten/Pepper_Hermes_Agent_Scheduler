from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def get(conn: sqlite3.Connection, loc_a: str, loc_b: str, default: int) -> int:
    if loc_a == loc_b:
        return 0
    row = conn.execute(
        "SELECT minutes FROM travel WHERE (loc_a = ? AND loc_b = ?) OR (loc_a = ? AND loc_b = ?)",
        (loc_a, loc_b, loc_b, loc_a),
    ).fetchone()
    return row["minutes"] if row else default


def put(conn: sqlite3.Connection, loc_a: str, loc_b: str, minutes: int, source: str = "manual") -> None:
    conn.execute(
        "INSERT INTO travel (loc_a, loc_b, minutes, source, updated_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(loc_a, loc_b) DO UPDATE SET minutes = excluded.minutes, "
        "source = excluded.source, updated_at = excluded.updated_at",
        (loc_a, loc_b, minutes, source, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
