from __future__ import annotations

import sqlite3

from pepper.repositories import objective_repo


def modifiers(conn: sqlite3.Connection, type_id: int | None) -> list[float]:
    """Active objectives contribute bounded soft weights to matching items."""
    out: list[float] = []
    for o in objective_repo.active(conn):
        if o["target_type_id"] in (None, type_id):
            out.append(float(o["weight"]))
    return out
