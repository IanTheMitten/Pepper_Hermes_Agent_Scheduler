from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from pepper.cascade.block import Block
from pepper.cascade.engine import solve
from pepper.cascade.gate import decide
from pepper.repositories import conflict_repo, item_repo, travel_repo
from pepper.rules import engine as rule_engine
from pepper.time_util import parse_iso, to_iso

ANCHOR_RIGIDITY = 0.85
DEFAULT_TRAVEL = 20  # minutes for an unknown pair (tune-later)


@dataclass(frozen=True)
class CascadeResult:
    action: str
    moved: dict[int, str]            # item_id -> human note
    options: list                    # escalate: described feasible options; else []
    conflicts: list = field(default_factory=list)  # impossible: contested windows + items


def _day_bounds(day: str) -> tuple[datetime, int, int]:
    base = parse_iso(f"{day}T00:00:00+00:00")
    return base, 0, 24 * 60


def _to_minutes(base: datetime, iso: str) -> int:
    return int((parse_iso(iso) - base).total_seconds() // 60)


def _to_iso(base: datetime, minutes: int) -> str:
    return to_iso(base + timedelta(minutes=minutes))


def _load_blocks(conn: sqlite3.Connection, day: str) -> tuple[datetime, list[Block]]:
    base, day_start, day_end = _day_bounds(day)
    rows = item_repo.list_in_range(conn, f"{day}T00:00:00+00:00", f"{day}T23:59:59+00:00")
    blocks = []
    for it in rows:
        # Only active items participate in reflow. list_in_range returns all
        # statuses (shared with list_day); done/dropped/cancelled items keep
        # their stale times and must not be re-placed or re-logged.
        if it.status not in ("scheduled", "in_progress"):
            continue
        dur = it.duration_estimate or (_to_minutes(base, it.end_time) - _to_minutes(base, it.start_time))
        rigidity = it.rigidity_score if it.rigidity_score is not None else 0.4
        anchor = rigidity >= ANCHOR_RIGIDITY or it.temporal_class == "fixed_time"
        # A 'no_before' rule raises the legal start for MOVABLE blocks only.
        # A user-fixed anchor before the floor must stay put — forcing it past
        # the floor would make the day infeasible ("don't SCHEDULE before 9",
        # not "delete what's already pinned earlier").
        floor = rule_engine.earliest_floor(conn, it.type_id)
        earliest = day_start if anchor else max(day_start, floor)
        blocks.append(Block(
            id=it.id, start=_to_minutes(base, it.start_time), end=_to_minutes(base, it.end_time),
            min_duration=it.min_duration or dur, rigidity=rigidity,
            protection=it.protection_score if it.protection_score is not None else 0.5,
            location=it.location, divisible=(it.divisibility == "divisible"),
            earliest=earliest, latest=day_end,
            anchor=anchor,
        ))
    return base, blocks


def _travel_fn(conn: sqlite3.Connection):
    return lambda a, b: travel_repo.get(conn, a, b, default=DEFAULT_TRAVEL)


def _describe_options(conn, base, original_blocks, solutions) -> list[dict]:
    """Turn engine Solutions into LLM/human-readable option descriptions.

    Each option: {cost, moves:[...]}. A move is a relocation
    {item_id, title, from, to} or a drop {item_id, title, action: "drop"}.
    Read-only — describes; never writes.
    """
    by_id = {b.id: b for b in original_blocks}
    options: list[dict] = []
    for sol in solutions:
        moves: list[dict] = []
        for blk in sol.placed:
            before = by_id.get(blk.id)
            if before is None or (blk.start == before.start and blk.end == before.end):
                continue
            it = item_repo.get_item(conn, blk.id)
            moves.append({
                "item_id": blk.id,
                "title": it.title if it else None,
                "from": _to_iso(base, before.start),
                "to": _to_iso(base, blk.start),
            })
        for dropped_id in sol.dropped:
            it = item_repo.get_item(conn, dropped_id)
            moves.append({
                "item_id": dropped_id,
                "title": it.title if it else None,
                "action": "drop",
            })
        options.append({"cost": round(sol.cost, 3), "moves": moves})
    return options


def _detect_conflicts(conn, base, blocks) -> list[dict]:
    """Group overlapping blocks into contested clusters for Hermes to reason over.

    Deterministic, read-only: a single pass that merges any block into every
    cluster it overlaps (so transitively-overlapping items land together). Each
    cluster reports its spanning window and the competing items annotated with
    the priority signals the LLM needs. No second solve, no relaxation.
    """
    clusters: list[list] = []
    for blk in sorted(blocks, key=lambda b: b.start):
        touching = [cl for cl in clusters
                    if any(blk.start < o.end and o.start < blk.end for o in cl)]
        if not touching:
            clusters.append([blk])
            continue
        merged = [blk]
        for cl in touching:
            merged.extend(cl)
            clusters.remove(cl)
        clusters.append(merged)

    conflicts: list[dict] = []
    for cl in clusters:
        if len(cl) < 2:
            continue
        items = []
        for blk in sorted(cl, key=lambda b: b.start):
            it = item_repo.get_item(conn, blk.id)
            items.append({
                "item_id": blk.id,
                "title": it.title if it else None,
                "start": _to_iso(base, blk.start),
                "end": _to_iso(base, blk.end),
                "protection": blk.protection,
                "rigidity": blk.rigidity,
                "commitment": it.commitment if it else None,
                "stakes": it.stakes if it else None,
            })
        conflicts.append({
            "window": {
                "start": _to_iso(base, min(b.start for b in cl)),
                "end": _to_iso(base, max(b.end for b in cl)),
            },
            "items": items,
        })
    return conflicts


def reflow(conn: sqlite3.Connection, day: str) -> CascadeResult:
    base, blocks = _load_blocks(conn, day)
    if len(blocks) < 2:
        return CascadeResult("noop", {}, [])
    solutions = solve(blocks, _travel_fn(conn))
    decision = decide(solutions)
    if decision.action == "impossible":
        # No feasible arrangement without sacrificing a protected/fixed item.
        # Report the contested windows + competing items; Hermes reasons, asks
        # the user, and enacts. Pepper changes nothing on its own.
        conflicts = _detect_conflicts(conn, base, blocks)
        return CascadeResult("impossible", {}, [], conflicts)
    if decision.action == "escalate":
        # Close call: do NOT auto-apply. Hand the feasible options to Hermes to
        # choose and enact via pepper_reschedule / pepper_delay_item /
        # pepper_cancel_item. The day holds its current state until then.
        options = _describe_options(conn, base, blocks, decision.options)
        return CascadeResult("escalate", {}, options)
    moved = _apply(conn, base, blocks, decision.chosen)
    return CascadeResult("apply", moved, [])


def _apply(conn, base, original_blocks, solution) -> dict[int, str]:
    by_id = {b.id: b for b in original_blocks}
    moved: dict[int, str] = {}
    for blk in solution.placed:
        before = by_id[blk.id]
        if blk.start != before.start or blk.end != before.end:
            item_repo.set_times(conn, blk.id, _to_iso(base, blk.start), _to_iso(base, blk.end))
            moved[blk.id] = f"moved to {_to_iso(base, blk.start)}"
            conflict_repo.log(conn, item_a_id=blk.id, item_b_id=None,
                              resolution_method="auto", lever_used=solution.levers.get(blk.id, "shift"))
        # Compress/split shrink the block; persist the new duration so a later
        # reflow does not read the stale (larger) duration_estimate.
        if (blk.end - blk.start) != (before.end - before.start):
            item_repo.set_duration_estimate(conn, blk.id, blk.end - blk.start)
    for block_id, minutes in solution.deferred.items():
        # The split lever defers the tail; surface it instead of losing it
        # silently. (Materializing a follow-on item is a later milestone.)
        if minutes > 0:
            note = f"split: {minutes}min deferred"
            moved[block_id] = f"{moved[block_id]} ({note})" if block_id in moved else note
            conflict_repo.log(conn, item_a_id=block_id, item_b_id=None,
                              resolution_method="auto", lever_used="split")
    for dropped_id in solution.dropped:
        item_repo.set_status(conn, dropped_id, "dropped")
        moved[dropped_id] = "dropped"
        conflict_repo.log(conn, item_a_id=dropped_id, item_b_id=None,
                          resolution_method="auto", lever_used="drop")
    return moved


def delay_item(conn: sqlite3.Connection, item_id: int, minutes: int, day: str) -> CascadeResult:
    item = item_repo.get_item(conn, item_id)
    if item is None:
        raise ValueError(f"item {item_id} not found")
    if item.start_time and item.end_time and minutes:
        item_repo.set_times(
            conn, item_id,
            to_iso(parse_iso(item.start_time) + timedelta(minutes=minutes)),
            to_iso(parse_iso(item.end_time) + timedelta(minutes=minutes)),
        )
    return reflow(conn, day)


def reschedule(conn: sqlite3.Connection, item_id: int, new_start: str, new_end: str,
               day: str) -> CascadeResult:
    if item_repo.get_item(conn, item_id) is None:
        raise ValueError(f"item {item_id} not found")
    if parse_iso(new_end) <= parse_iso(new_start):
        raise ValueError("new_end must be after new_start")
    item_repo.set_times(conn, item_id, new_start, new_end)
    return reflow(conn, day)


def cancel_item(conn: sqlite3.Connection, item_id: int) -> None:
    """Cancel an item as a deliberate decision.

    Sets status to 'cancelled' (distinct from the learning-signal 'dropped'
    outcome) and writes NO learning observation — Hermes uses this to enact a
    "drop X" choice from a reflow escalate/impossible report.
    """
    if item_repo.get_item(conn, item_id) is None:
        raise ValueError(f"item {item_id} not found")
    item_repo.set_status(conn, item_id, "cancelled")
