from __future__ import annotations

import sqlite3
from datetime import timedelta

from pepper.learning import bias, habits
from pepper.planner.slots import free_slots
from pepper.repositories import item_repo, observation_repo, type_stats_repo, vector_repo
from pepper.time_util import parse_iso, to_iso

DEFAULT_MINUTES = 30
MAX_OPTIONS = 3


def _estimate(conn: sqlite3.Connection, item) -> tuple[int, str]:
    """Learned duration via the estimate back-off chain; falls back to the booked estimate."""
    if item.type_id is None:
        return item.duration_estimate or DEFAULT_MINUTES, "booked"
    stats = type_stats_repo.get(conn, item.type_id)
    confident = bool(stats and stats.avg_actual
                     and stats.confidence >= bias.TYPE_STATS_CONF_GATE)
    minutes = bias.estimate_minutes(
        conn, type_id=item.type_id,
        type_name=vector_repo.get_type_name(conn, item.type_id) or "",
        factors={"commitment": item.commitment, "divisibility": item.divisibility,
                 "stakes": item.stakes},
        fallback=item.duration_estimate or DEFAULT_MINUTES,
    )
    return minutes, ("learned" if confident else "bias_adjusted")


def suggest_slots(
    conn: sqlite3.Connection, item_id: int, day: str, *,
    day_start_min: int = 540, day_end_min: int = 1080,
) -> dict:
    """Rank the day's free slots for an item by learned time-of-day habit.

    Read-only: returns ranked options for Hermes/the user to choose from;
    enacting a choice goes through pepper_reschedule.
    """
    item = item_repo.get_item(conn, item_id)
    if item is None:
        raise ValueError(f"item {item_id} not found")
    duration, source = _estimate(conn, item)
    affinity = (habits.tod_affinity(observation_repo.list_by_type(conn, item.type_id))
                if item.type_id is not None else {})
    options = []
    for slot in free_slots(conn, day, day_start_min=day_start_min,
                           day_end_min=day_end_min, min_minutes=15):
        if slot.minutes < duration:
            continue
        start = parse_iso(slot.start)
        bucket = habits.tod_bucket(start.hour)
        options.append({
            "start": slot.start,
            "end": to_iso(start + timedelta(minutes=duration)),
            "time_of_day": bucket,
            "habit_score": affinity.get(bucket, 0.0) if affinity else None,
        })
    options.sort(key=lambda o: (-(o["habit_score"] or 0.0), o["start"]))
    return {
        "item_id": item.id,
        "duration_minutes": duration,
        "duration_source": source,
        "options": options[:MAX_OPTIONS],
    }
