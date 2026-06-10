from __future__ import annotations

import sqlite3

from pepper.learning import bias
from pepper.learning.estimator import confidence, fold
from pepper.repositories import item_repo, observation_repo, type_stats_repo


def recompute(conn: sqlite3.Connection, type_id: int) -> None:
    """Rebuild Layer 2 type_stats from the immutable Layer 1 observations."""
    obs = observation_repo.list_by_type(conn, type_id)
    if not obs:
        return
    done = [o for o in obs if o.actual is not None and o.outcome in ("done", "partial")]
    actuals = [float(o.actual) for o in done]
    avg_actual, spread, n = fold(actuals) if actuals else (None, None, 0)

    overruns = [float(o.actual - o.estimated) for o in done if o.estimated is not None]
    overrun, _, _ = fold(overruns) if overruns else (None, None, 0)

    slips = [float(o.start_slip) for o in obs if o.start_slip is not None]
    avg_slip, _, _ = fold(slips) if slips else (None, None, 0)

    scoped = [o for o in done if o.scope_reached and o.scope_reached > 0]
    per_unit = [float(o.actual) / o.scope_reached for o in scoped]
    tps_unit, _, _ = fold(per_unit) if per_unit else (None, None, 0)

    dropped = sum(1 for o in obs if o.outcome == "dropped_pressure")
    drop_tendency = dropped / len(obs)

    conf = confidence(n, spread or 0.0, avg_actual or 0.0) if actuals else 0.0
    type_stats_repo.upsert(
        conn, type_id,
        avg_actual=avg_actual, overrun=overrun, avg_start_slip=avg_slip, spread=spread,
        sample_count=len(obs), confidence=conf, time_per_scope_unit=tps_unit,
        drop_tendency=drop_tendency,
    )


def record_completion(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    actual_minutes: int,
    outcome: str,
    scope_reached: float | None = None,
) -> None:
    item = item_repo.get_item(conn, item_id)
    if item is None:
        raise ValueError(f"unknown item {item_id}")
    observation_repo.append(
        conn, type_id=item.type_id, item_id=item.id, estimated=item.duration_estimate,
        actual=actual_minutes, scheduled_start=item.start_time, scope_reached=scope_reached,
        outcome=outcome, location=item.location,
    )
    if item.type_id is not None:
        recompute(conn, item.type_id)
    if item.duration_estimate and item.duration_estimate > 0 and outcome in ("done", "partial"):
        ratio = actual_minutes / item.duration_estimate
        bias.record_factor_bias(
            conn,
            {"commitment": item.commitment, "divisibility": item.divisibility,
             "stakes": item.stakes},
            ratio,
        )
    status = "done" if outcome == "done" else ("dropped" if "dropped" in outcome else "in_progress")
    item_repo.set_status(conn, item_id, status)
