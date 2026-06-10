from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Goal:
    id: int
    item_id: int | None
    total_scope: float | None
    scope_done: float
    granularity: str


def create(conn, item_id, *, description=None, granularity="coarse", total_scope=None,
           source="elicited") -> int:
    cur = conn.execute(
        "INSERT INTO goals (item_id, description, granularity, total_scope, source, updated_at) "
        "VALUES (?,?,?,?,?,?)",
        (item_id, description, granularity, total_scope, source,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_for_item(conn, item_id) -> Goal | None:
    r = conn.execute("SELECT * FROM goals WHERE item_id = ?", (item_id,)).fetchone()
    return Goal(r["id"], r["item_id"], r["total_scope"], r["scope_done"], r["granularity"]) if r else None
