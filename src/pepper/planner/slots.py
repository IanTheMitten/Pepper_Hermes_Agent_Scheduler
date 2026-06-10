from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta

from pepper.repositories import item_repo
from pepper.time_util import parse_iso, to_iso


@dataclass(frozen=True)
class Slot:
    start: str
    end: str
    minutes: int


def free_slots(conn: sqlite3.Connection, day: str, *, day_start_min: int, day_end_min: int,
               min_minutes: int) -> list[Slot]:
    base = parse_iso(f"{day}T00:00:00+00:00")
    items = item_repo.list_in_range(conn, f"{day}T00:00:00+00:00", f"{day}T23:59:59+00:00")
    busy = sorted(
        ((int((parse_iso(i.start_time) - base).total_seconds() // 60),
          int((parse_iso(i.end_time) - base).total_seconds() // 60))
         for i in items if i.status in ("scheduled", "in_progress")),
        key=lambda x: x[0],
    )
    slots: list[Slot] = []
    cursor = day_start_min
    for s, e in busy:
        if s - cursor >= min_minutes:
            slots.append(_slot(base, cursor, s))
        cursor = max(cursor, e)
    if day_end_min - cursor >= min_minutes:
        slots.append(_slot(base, cursor, day_end_min))
    return slots


def _slot(base, start_min: int, end_min: int) -> Slot:
    start = to_iso(base + timedelta(minutes=start_min))
    end = to_iso(base + timedelta(minutes=end_min))
    return Slot(start, end, end_min - start_min)
