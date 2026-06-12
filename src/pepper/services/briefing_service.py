from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import timedelta

from pepper.domain.item import Item
from pepper.planner.projection import project
from pepper.repositories import item_repo, type_stats_repo
from pepper.time_util import overlaps, parse_iso

DRIFT_MIN_CONFIDENCE = 0.5   # type_stats confidence below this -> stay silent (tune-later)
DRIFT_THRESHOLD = 0.25       # relative divergence booked vs learned that warrants a warning
DEADLINE_LOOKAHEAD_DAYS = 7  # unscheduled tasks due within this window are "looming"

_ACTIVE = ("scheduled", "in_progress")


def build_briefing(conn: sqlite3.Connection, day: str) -> dict:
    """Proactive day digest: composes existing reflex signals, computes nothing new."""
    scheduled = [
        i for i in item_repo.list_in_range(conn, f"{day}T00:00:00+00:00", f"{day}T23:59:59+00:00")
        if i.status in _ACTIVE
    ]
    open_deadline = item_repo.list_open_deadline_items(conn)
    return {
        "schedule": [asdict(i) for i in scheduled],
        "overlaps": _find_overlaps(scheduled),
        "at_risk": _at_risk(conn, open_deadline, day),
        "estimate_drift": _estimate_drift(conn, scheduled),
        "unscheduled_deadlines": _unscheduled_deadlines(open_deadline, day),
    }


def _find_overlaps(items: list[Item]) -> list[dict]:
    found = []
    for idx, a in enumerate(items):
        for b in items[idx + 1:]:
            if overlaps(a.start_time, a.end_time, b.start_time, b.end_time):
                found.append({"item_ids": [a.id, b.id], "titles": [a.title, b.title]})
    return found


def _at_risk(conn: sqlite3.Connection, open_deadline: list[Item], day: str) -> list[dict]:
    risks = []
    for item in open_deadline:
        p = project(conn, item.id, from_day=day)
        if p.status == "at_risk":
            risks.append({
                "item_id": item.id, "title": item.title, "deadline": item.deadline,
                "remaining_effort": p.remaining_effort, "free_capacity": p.free_capacity,
            })
    return risks


def _estimate_drift(conn: sqlite3.Connection, items: list[Item]) -> list[dict]:
    warnings = []
    for item in items:
        if item.type_id is None or not item.duration_estimate:
            continue
        stats = type_stats_repo.get(conn, item.type_id)
        if stats is None or not stats.avg_actual or stats.confidence < DRIFT_MIN_CONFIDENCE:
            continue
        if abs(stats.avg_actual - item.duration_estimate) / item.duration_estimate >= DRIFT_THRESHOLD:
            warnings.append({
                "item_id": item.id, "title": item.title,
                "booked_minutes": item.duration_estimate,
                "learned_minutes": round(stats.avg_actual),
            })
    return warnings


def _unscheduled_deadlines(open_deadline: list[Item], day: str) -> list[dict]:
    horizon = parse_iso(f"{day}T00:00:00+00:00") + timedelta(days=DEADLINE_LOOKAHEAD_DAYS)
    return [
        {"item_id": i.id, "title": i.title, "deadline": i.deadline,
         "duration_estimate": i.duration_estimate}
        for i in open_deadline
        if i.start_time is None and parse_iso(i.deadline) <= horizon
    ]
