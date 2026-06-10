from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from pepper.time_util import parse_iso


@dataclass(frozen=True)
class Observation:
    id: int
    type_id: int | None
    item_id: int | None
    estimated: int | None
    actual: int | None
    start_slip: int | None
    scope_reached: float | None
    outcome: str
    day_of_week: int | None
    time_of_day: str | None


def _tod_bucket(hour: int) -> str:
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def append(
    conn: sqlite3.Connection,
    *,
    type_id: int | None,
    item_id: int | None,
    estimated: int | None,
    actual: int | None,
    outcome: str,
    scheduled_start: str | None = None,
    actual_start: str | None = None,
    start_slip: int | None = None,
    scope_reached: float | None = None,
    location: str | None = None,
    preceded_by: int | None = None,
) -> int:
    dow: int | None = None
    tod: str | None = None
    if scheduled_start is not None:
        dt = parse_iso(scheduled_start)
        dow = dt.weekday()
        tod = _tod_bucket(dt.hour)
    cur = conn.execute(
        "INSERT INTO observations (type_id, item_id, estimated, actual, scheduled_start, "
        "actual_start, start_slip, scope_reached, outcome, day_of_week, time_of_day, "
        "location, preceded_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (type_id, item_id, estimated, actual, scheduled_start, actual_start, start_slip,
         scope_reached, outcome, dow, tod, location, preceded_by,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_by_type(conn: sqlite3.Connection, type_id: int) -> list[Observation]:
    rows = conn.execute(
        "SELECT * FROM observations WHERE type_id = ? ORDER BY id", (type_id,)
    ).fetchall()
    return [
        Observation(
            id=r["id"], type_id=r["type_id"], item_id=r["item_id"], estimated=r["estimated"],
            actual=r["actual"], start_slip=r["start_slip"], scope_reached=r["scope_reached"],
            outcome=r["outcome"], day_of_week=r["day_of_week"], time_of_day=r["time_of_day"],
        )
        for r in rows
    ]
