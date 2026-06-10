from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta

from pepper.planner.slots import free_slots
from pepper.repositories import goal_repo, item_repo, type_stats_repo
from pepper.time_util import parse_iso

HORIZON_DAYS = 30


@dataclass(frozen=True)
class Projection:
    status: str            # "on_track" | "at_risk"
    remaining_effort: int
    free_capacity: int


def _remaining_effort(conn: sqlite3.Connection, item) -> int:
    """Honest estimate: scope-driven via learned time_per_scope_unit when available."""
    goal = goal_repo.get_for_item(conn, item.id)
    if goal and goal.total_scope and item.type_id is not None:
        stats = type_stats_repo.get(conn, item.type_id)
        if stats and stats.time_per_scope_unit:
            return round((goal.total_scope - goal.scope_done) * stats.time_per_scope_unit)
    return item.effort_estimate or 0


def project(conn: sqlite3.Connection, item_id: int, *, from_day: str,
            day_start_min: int = 540, day_end_min: int = 1080) -> Projection:
    item = item_repo.get_item(conn, item_id)
    if item is None or not item.deadline:
        return Projection("on_track", 0, 0)
    remaining = _remaining_effort(conn, item)
    capacity = 0
    day = parse_iso(f"{from_day}T00:00:00+00:00")
    deadline = parse_iso(item.deadline)
    start = day
    while day < deadline and (day - start).days < HORIZON_DAYS:
        for slot in free_slots(conn, day.date().isoformat(), day_start_min=day_start_min,
                               day_end_min=day_end_min, min_minutes=15):
            capacity += slot.minutes
        day += timedelta(days=1)
    status = "at_risk" if remaining > capacity else "on_track"
    return Projection(status, remaining, capacity)
