from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from pepper.load.gauge import acute_load, protection_multiplier
from pepper.objectives import engine as objective_engine
from pepper.priority.scores import compute_scores, slack_ratio
from pepper.repositories import item_repo, person_repo
from pepper.rules import engine as rule_engine
from pepper.time_util import parse_iso


def _counterparty_weight(conn: sqlite3.Connection, counterparty_id: int | None) -> str:
    if counterparty_id is None:
        return "none"
    person = person_repo.get(conn, counterparty_id)
    return person.counterparty_weight if person else "none"


def _slack(item) -> float | None:
    if item.temporal_class != "deadline" or not item.deadline:
        return None
    now = datetime.now(timezone.utc)
    open_minutes = (parse_iso(item.deadline) - now).total_seconds() / 60.0
    remaining_effort = float(item.effort_estimate or item.duration_estimate or 0)
    return slack_ratio(open_minutes, remaining_effort)


def recompute_scores(conn: sqlite3.Connection, item_id: int) -> None:
    item = item_repo.get_item(conn, item_id)
    if item is None:
        return
    r, p = compute_scores(
        temporal_class=item.temporal_class,
        commitment=item.commitment,
        counterparty_weight=_counterparty_weight(conn, item.counterparty_id),
        stakes=item.stakes,
        item_slack_ratio=_slack(item),
        modifiers=[],  # objectives/load/prefs join in M6/M7
    )
    item_repo.set_scores(conn, item_id, r, p)


def _day_load(conn: sqlite3.Connection, day: str) -> float:
    """Cheap acute proxy: density from how full the day already is (tune-later)."""
    items = item_repo.list_in_range(conn, f"{day}T00:00:00+00:00", f"{day}T23:59:59+00:00")
    active = [i for i in items if i.status in ("scheduled", "in_progress")]
    busy_minutes = sum((i.duration_estimate or 0) for i in active)
    density = min(1.0, busy_minutes / (10 * 60))  # vs a 10h reference day
    return acute_load(density=density, day_length=density, context_switch=min(1.0, len(active) / 8))


def _gather_modifiers(conn: sqlite3.Connection, item, day: str) -> list[float]:
    mods = rule_engine.cost_modifiers(conn, item.type_id)
    mods += objective_engine.modifiers(conn, item.type_id)
    load = _day_load(conn, day)
    is_low_stakes = item.stakes == "trivial_repeatable" or (item.protection_score or 0) < 0.25
    is_recovery = item.commitment == "promise_to_self"
    mods.append(protection_multiplier(load, is_recovery=is_recovery, is_low_stakes=is_low_stakes))
    return mods


def recompute_with_context(conn: sqlite3.Connection, item_id: int, day: str) -> float:
    """Recompute R/P with the soft layers (rules + objectives + load) blended in.
    Returns the resulting protection_score for convenience."""
    item = item_repo.get_item(conn, item_id)
    if item is None:
        return 0.0
    r, p = compute_scores(
        temporal_class=item.temporal_class, commitment=item.commitment,
        counterparty_weight=_counterparty_weight(conn, item.counterparty_id),
        stakes=item.stakes, item_slack_ratio=_slack(item),
        modifiers=_gather_modifiers(conn, item, day),
    )
    item_repo.set_scores(conn, item_id, r, p)
    return p
