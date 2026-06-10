from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from pepper.learning.estimator import CONFIDENCE_GATE
from pepper.learning.seeds import seed_estimate
from pepper.repositories import type_stats_repo

BIAS_MIN, BIAS_MAX = 0.5, 2.0
BIAS_ALPHA = 0.15  # damped (tune-later)
TYPE_STATS_CONF_GATE = 0.5


def _axes(factors: dict) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    if "commitment" in factors:
        keys.append(("social", factors["commitment"]))
    if "divisibility" in factors:
        keys.append(("character", factors["divisibility"]))
    if "stakes" in factors:
        keys.append(("stakes", factors["stakes"]))
    if "time_of_day" in factors:
        keys.append(("time_of_day", factors["time_of_day"]))
    return keys


def get_bias(conn: sqlite3.Connection, axis: str, value: str) -> float:
    r = conn.execute(
        "SELECT bias_factor FROM user_bias WHERE axis = ? AND value = ?", (axis, value)
    ).fetchone()
    return r["bias_factor"] if r else 1.0


def update_bias(conn: sqlite3.Connection, axis: str, value: str, ratio: float) -> None:
    r = conn.execute(
        "SELECT bias_factor, sample_count FROM user_bias WHERE axis = ? AND value = ?",
        (axis, value),
    ).fetchone()
    current = r["bias_factor"] if r else 1.0
    updated = current + BIAS_ALPHA * (ratio - current)
    updated = max(BIAS_MIN, min(BIAS_MAX, updated))
    count = (r["sample_count"] if r else 0) + 1
    conn.execute(
        "INSERT INTO user_bias (axis, value, bias_factor, sample_count, confidence, updated_at) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(axis, value) DO UPDATE SET "
        "bias_factor = excluded.bias_factor, sample_count = excluded.sample_count, "
        "confidence = excluded.confidence, updated_at = excluded.updated_at",
        (axis, value, updated, count, min(1.0, count / CONFIDENCE_GATE),
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def record_factor_bias(conn: sqlite3.Connection, factors: dict, ratio: float) -> None:
    for axis, value in _axes(factors):
        update_bias(conn, axis, value, ratio)


def estimate_minutes(
    conn: sqlite3.Connection, *, type_id: int, type_name: str, factors: dict, fallback: int
) -> int:
    """Back-off chain: confident type_stats -> seed x personal-bias product -> fallback."""
    stats = type_stats_repo.get(conn, type_id)
    if stats and stats.avg_actual and stats.confidence >= TYPE_STATS_CONF_GATE:
        return round(stats.avg_actual)
    seed = seed_estimate(type_name)
    base = float(seed["duration"]) if seed else float(fallback)
    factor = 1.0
    for axis, value in _axes(factors):
        factor *= get_bias(conn, axis, value)
    factor = max(BIAS_MIN, min(BIAS_MAX, factor))
    return round(base * factor)
