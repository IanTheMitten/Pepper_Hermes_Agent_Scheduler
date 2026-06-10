from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def log(
    conn: sqlite3.Connection,
    *,
    item_a_id: int | None,
    item_b_id: int | None,
    resolution_method: str,
    lever_used: str,
) -> None:
    conn.execute(
        "INSERT INTO conflicts (item_a_id, item_b_id, resolution_method, lever_used, resolved_at) "
        "VALUES (?,?,?,?,?)",
        (item_a_id, item_b_id, resolution_method, lever_used,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
