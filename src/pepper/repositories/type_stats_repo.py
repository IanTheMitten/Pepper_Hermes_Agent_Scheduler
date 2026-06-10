from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TypeStats:
    type_id: int
    avg_actual: float | None
    overrun: float | None
    avg_start_slip: float | None
    spread: float | None
    sample_count: int
    confidence: float
    time_per_scope_unit: float | None
    drop_tendency: float | None


def get(conn: sqlite3.Connection, type_id: int) -> TypeStats | None:
    r = conn.execute("SELECT * FROM type_stats WHERE type_id = ?", (type_id,)).fetchone()
    if r is None:
        return None
    return TypeStats(
        type_id=r["type_id"], avg_actual=r["avg_actual"], overrun=r["overrun"],
        avg_start_slip=r["avg_start_slip"], spread=r["spread"], sample_count=r["sample_count"],
        confidence=r["confidence"], time_per_scope_unit=r["time_per_scope_unit"],
        drop_tendency=r["drop_tendency"],
    )


def upsert(conn: sqlite3.Connection, type_id: int, **fields) -> None:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    cols = ["type_id", *fields.keys()]
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{k} = excluded.{k}" for k in fields)
    conn.execute(
        f"INSERT INTO type_stats ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(type_id) DO UPDATE SET {updates}",
        (type_id, *fields.values()),
    )
    conn.commit()
