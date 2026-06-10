from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from pepper.planner.projection import Projection, project
from pepper.repositories import goal_repo, item_repo
from pepper.services import priority_service


def set_deadline(
    conn: sqlite3.Connection, item_id: int, *, deadline: str, effort_minutes: int,
    total_scope: float | None = None,
) -> None:
    if item_repo.get_item(conn, item_id) is None:
        raise ValueError(f"item {item_id} not found")
    item_repo.set_deadline_fields(conn, item_id, deadline, effort_minutes)
    if goal_repo.get_for_item(conn, item_id) is None:
        goal_repo.create(conn, item_id, granularity="coarse", total_scope=total_scope,
                         source="elicited")
    priority_service.recompute_scores(conn, item_id)


@dataclass(frozen=True)
class Rollup:
    status: str
    remaining_effort: int
    free_capacity: int


def project_rollup(conn: sqlite3.Connection, project_id: int, *, from_day: str) -> Rollup:
    members = item_repo.list_by_project(conn, project_id)
    remaining = 0
    capacity = 0
    for m in members:
        p: Projection = project(conn, m.id, from_day=from_day)
        remaining += p.remaining_effort
        capacity = max(capacity, p.free_capacity)  # shared calendar -> shared capacity
    status = "at_risk" if remaining > capacity else "on_track"
    return Rollup(status, remaining, capacity)
