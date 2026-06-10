"""Robustness / stress regression tests.

These lock in cross-cutting invariants surfaced by stress testing: the cascade
engine never returns an infeasible solution and never reports a *solvable* day as
impossible (no node-budget false-negatives); oversubscription is shed by dropping
droppable items while genuinely over-constrained (all-anchor) days cause no data
loss; the soft-modifier blend stays bounded under heavy stacking; the load gauge
clamps out-of-range inputs; and the learning loop survives extreme observations.

Deterministic only — no timing assertions (the node budget guarantees termination
structurally, so a test that returns at all proves termination).
"""
from __future__ import annotations

from datetime import datetime, timezone

from pepper.cascade.block import Block
from pepper.cascade.constraints import feasible
from pepper.cascade.engine import solve
from pepper.load.gauge import (
    MOD_MAX,
    MOD_MIN,
    acute_load,
    chronic_load,
    protection_multiplier,
    total_load,
)
from pepper.priority.scores import MODIFIER_MAX, base_protection
from pepper.repositories import (
    item_repo,
    objective_repo,
    rule_repo,
    type_stats_repo,
    vector_repo,
)
from pepper.services import (
    cascade_service,
    learning_service,
    planner_service,
    priority_service,
    schedule_service,
)

ZERO = lambda a, b: 0  # noqa: E731


def _b(i, start, end, **kw):
    return Block(
        id=i, start=start, end=end, min_duration=kw.get("min", end - start),
        rigidity=kw.get("r", 0.4), protection=kw.get("p", 0.4), location=kw.get("loc"),
        divisible=kw.get("div", False), earliest=kw.get("e", 0), latest=kw.get("l", 1440),
        anchor=kw.get("anchor", False),
    )


def _iso(h=0, mi=0, d=9):
    return datetime(2026, 6, d, h, mi, tzinfo=timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Cascade engine: feasibility & no false-negatives
# --------------------------------------------------------------------------- #
def test_engine_never_returns_infeasible_solution_under_heavy_overlap():
    # 30 unmovable 60-min blocks fighting for one 60-min window: unsatisfiable.
    blocks = [_b(i, 540, 600, min=60, p=0.9, e=540, l=600) for i in range(30)]
    sols = solve(blocks, ZERO)
    # solve may return [] (impossible) but must NEVER return an infeasible arrangement.
    assert all(feasible([*s.placed, *s.anchors], ZERO) for s in sols)


def test_engine_packs_exact_tiling_no_false_negative():
    # 10x 60-min blocks all initially overlapping at 540-600, window 480-1080 (=600 min):
    # the ONLY feasible answer is the perfect back-to-back tiling. The bounded search
    # must still find it (regression guard against node-budget false-negatives).
    blocks = [_b(i, 540, 600, min=60, p=0.9, e=480, l=1080) for i in range(10)]
    sols = solve(blocks, ZERO)
    assert sols, "solvable exact-tiling reported impossible (false-negative)"
    assert sols[0].is_feasible
    starts = sorted(b.start for b in sols[0].placed)
    assert starts == list(range(480, 1080, 60))


def test_engine_solves_forced_reverse_order():
    # 6 blocks whose windows force a strict order opposite to their initial order.
    blocks = [_b(i, 0, 60, min=60, p=0.9, e=(5 - i) * 60 + 480, l=(5 - i) * 60 + 540)
              for i in range(6)]
    sols = solve(blocks, ZERO)
    assert sols, "solvable forced-order reported impossible (false-negative)"
    assert sols[0].is_feasible


def test_engine_sheds_excess_when_all_droppable():
    # 12x 60-min low-protection blocks, window only fits 4 -> excess must be dropped.
    blocks = [_b(i, 540, 600, min=60, p=0.1, e=480, l=720) for i in range(12)]
    sols = solve(blocks, ZERO)
    assert sols, "should be feasible by dropping low-protection items"
    best = sols[0]
    assert best.is_feasible
    assert best.dropped, "expected excess items to be dropped"
    assert len(best.placed) + len(best.dropped) == 12


def test_engine_respects_travel_gaps():
    travel = lambda a, b: 30 if a != b else 0  # noqa: E731
    blocks = [_b(1, 540, 600, loc="A", e=480, l=1080),
              _b(2, 600, 660, loc="B", e=480, l=1080)]
    sols = solve(blocks, travel)
    assert sols
    assert feasible([*sols[0].placed, *sols[0].anchors], travel)


def test_engine_scales_to_many_non_overlapping_blocks():
    blocks = [_b(i, i * 7, i * 7 + 5) for i in range(200)]
    sols = solve(blocks, ZERO)
    assert sols and sols[0].is_feasible


# --------------------------------------------------------------------------- #
# Reflow service: oversubscription vs. genuine impossibility
# --------------------------------------------------------------------------- #
def test_reflow_resolves_oversubscribed_droppable_day(conn):
    for i in range(30):
        it = schedule_service.add_event(conn=conn, title=f"e{i}", start_time=_iso(h=9),
                                        end_time=_iso(h=10))
        item_repo.set_factors(conn, it.id, temporal_class="anytime",
                              stakes="trivial_repeatable")
        priority_service.recompute_scores(conn, it.id)
    res = cascade_service.reflow(conn, day="2026-06-09")
    assert res.action in ("apply", "escalate")
    assert any(v == "dropped" for v in res.moved.values()), "expected excess to be dropped"


def test_reflow_impossible_day_causes_no_data_loss(conn):
    # 30 fixed-time anchors stacked on the same hour: genuinely unsatisfiable.
    ids = []
    for i in range(30):
        it = schedule_service.add_event(conn=conn, title=f"a{i}", start_time=_iso(h=9),
                                        end_time=_iso(h=10))
        priority_service.recompute_scores(conn, it.id)
        ids.append(it.id)
    res = cascade_service.reflow(conn, day="2026-06-09")
    # Current behavior: reported impossible. Invariant that must hold regardless of how
    # impossibility is later surfaced: fixed commitments are never silently moved/dropped.
    assert res.action == "impossible"
    for item_id in ids:
        row = item_repo.get_item(conn, item_id)
        assert row.start_time == _iso(h=9)
        assert row.status == "scheduled"


# --------------------------------------------------------------------------- #
# Intelligence layers: bounded under stress
# --------------------------------------------------------------------------- #
def test_load_gauge_clamps_out_of_range_inputs():
    assert 0.0 <= acute_load(1.0, 1.0, 1.0) <= 1.0
    assert 0.0 <= acute_load(-5.0, 99.0, 0.5) <= 1.0  # negatives / >1 clamped
    assert 0.0 <= chronic_load(0.9, 100, rested=False) <= 1.0  # huge debt clamped
    assert 0.0 <= total_load(5.0, -3.0) <= 1.0


def test_protection_multiplier_bounded_at_extreme_load():
    hi = total_load(acute=1.0, chronic=1.0)
    assert MOD_MIN <= protection_multiplier(hi, is_recovery=True, is_low_stakes=False) <= MOD_MAX
    assert MOD_MIN <= protection_multiplier(hi, is_recovery=False, is_low_stakes=True) <= MOD_MAX
    # recovery nudges up, low-stakes nudges down
    assert protection_multiplier(hi, is_recovery=True, is_low_stakes=False) > 1.0
    assert protection_multiplier(hi, is_recovery=False, is_low_stakes=True) < 1.0


def test_stacked_rules_and_objectives_stay_bounded(conn):
    t = 7
    it = schedule_service.add_task(conn=conn, title="deep work", duration_estimate=90)
    item_repo.set_type(conn, it.id, t)
    for _ in range(10):
        rule_repo.add(conn, kind="cost_bias", target_type_id=t, param="1.25")
        objective_repo.create(conn, "obj", target_type_id=t, weight=1.25)
    p = priority_service.recompute_with_context(conn, it.id, day="2026-06-09")
    # base_P x bounded aggregate modifier: 20 up-modifiers must clamp to base_P * MODIFIER_MAX.
    base = base_protection(commitment="solo", counterparty_weight="none", stakes="reschedulable")
    assert abs(p - base * MODIFIER_MAX) < 1e-6


# --------------------------------------------------------------------------- #
# Learning loop: survives extreme observations
# --------------------------------------------------------------------------- #
def test_learning_survives_extreme_actuals(conn):
    t = vector_repo.create_type(conn, "weird")
    for val in (0, 100_000, 1, 99_999, 0):
        it = schedule_service.add_event(conn=conn, title="weird", start_time=_iso(h=7),
                                        end_time=_iso(h=8))
        item_repo.set_type(conn, it.id, t)
        learning_service.record_completion(conn, it.id, actual_minutes=val, outcome="done")
    stats = type_stats_repo.get(conn, t)
    assert stats.sample_count == 5
    assert 0.0 <= stats.confidence <= 1.0
    assert stats.spread >= 0.0


def test_past_deadline_rigidity_stays_bounded(conn):
    it = schedule_service.add_task(conn=conn, title="urgent", duration_estimate=600)
    planner_service.set_deadline(
        conn, it.id, deadline=datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
        effort_minutes=600,
    )
    row = item_repo.get_item(conn, it.id)
    assert row.rigidity_score is None or 0.0 <= row.rigidity_score <= 1.0
    assert row.protection_score is None or 0.0 <= row.protection_score <= 2.0
