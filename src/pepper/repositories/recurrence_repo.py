from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Recurrence:
    id: int
    title: str
    type_id: int | None
    freq: str
    interval: int
    byday: str | None
    at_time: str
    duration_estimate: int
    until: str | None
    location: str | None
    commitment: str
    counterparty_id: int | None
    temporal_class: str
    stakes: str
    divisibility: str
    materialized_through: str | None


def create(conn, **fields) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cols = (
        "title type_id freq interval byday at_time duration_estimate until location "
        "commitment counterparty_id temporal_class stakes divisibility"
    ).split()
    values = [fields.get(c) for c in cols]
    cur = conn.execute(
        f"INSERT INTO recurrence ({', '.join(cols)}, created_at, updated_at) "
        f"VALUES ({', '.join('?' for _ in cols)}, ?, ?)",
        (*values, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn, recurrence_id) -> Recurrence | None:
    r = conn.execute("SELECT * FROM recurrence WHERE id = ?", (recurrence_id,)).fetchone()
    if r is None:
        return None
    return Recurrence(
        r["id"], r["title"], r["type_id"], r["freq"], r["interval"], r["byday"], r["at_time"],
        r["duration_estimate"], r["until"], r["location"], r["commitment"], r["counterparty_id"],
        r["temporal_class"], r["stakes"], r["divisibility"], r["materialized_through"],
    )


def update_fields(conn, recurrence_id, **fields) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE recurrence SET {assignments}, updated_at = ? WHERE id = ?",
        (*fields.values(), datetime.now(timezone.utc).isoformat(), recurrence_id),
    )
    conn.commit()


def set_materialized_through(conn, recurrence_id, through: str) -> None:
    conn.execute("UPDATE recurrence SET materialized_through = ? WHERE id = ?",
                 (through, recurrence_id))
    conn.commit()
