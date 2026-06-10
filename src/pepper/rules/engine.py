from __future__ import annotations

import sqlite3

from pepper.repositories import rule_repo

DEFAULT_EARLIEST = 480  # 08:00 (tune-later)


def earliest_floor(conn: sqlite3.Connection, type_id: int | None) -> int:
    """Compiled 'no_before' rules raise the earliest legal start (a hard window)."""
    floor = DEFAULT_EARLIEST
    for r in rule_repo.by_kind(conn, "no_before"):
        if r["target_type_id"] in (None, type_id):
            h, m = (int(x) for x in r["param"].split(":"))
            floor = max(floor, h * 60 + m)
    return floor


def cost_modifiers(conn: sqlite3.Connection, type_id: int | None) -> list[float]:
    """Compiled 'cost_bias' rules become bounded soft modifiers (clamped by effective_protection)."""
    mods: list[float] = []
    for r in rule_repo.by_kind(conn, "cost_bias"):
        if r["target_type_id"] in (None, type_id):
            mods.append(float(r["param"]))
    return mods
