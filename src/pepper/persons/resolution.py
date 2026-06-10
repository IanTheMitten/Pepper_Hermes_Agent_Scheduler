from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from pepper.repositories import person_repo

MARGIN = 1  # minimum score lead to pick silently (tune-later)


@dataclass(frozen=True)
class Resolution:
    status: str  # "found" | "none" | "ambiguous"
    person_id: int | None
    candidates: list[int]


def _score(conn: sqlite3.Connection, person_id: int, context: dict) -> int:
    if not context:
        return 0
    signals = person_repo.get_context(conn, person_id)
    total = 0
    for sig in signals:
        if context.get(sig.signal_type) == sig.signal_value:
            total += sig.count
    return total


def resolve(conn: sqlite3.Connection, name: str, context: dict) -> Resolution:
    ids = person_repo.find_by_name(conn, name)
    if not ids:
        return Resolution("none", None, [])
    if len(ids) == 1:
        return Resolution("found", ids[0], ids)
    scored = sorted(((_score(conn, pid, context), pid) for pid in ids), reverse=True)
    best_score, best_id = scored[0]
    second_score = scored[1][0]
    if best_score - second_score >= MARGIN:
        return Resolution("found", best_id, ids)
    return Resolution("ambiguous", None, ids)
