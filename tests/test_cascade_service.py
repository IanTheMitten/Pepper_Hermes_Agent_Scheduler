import pytest

from pepper.cascade.block import Block
from pepper.cascade.engine import Solution
from pepper.repositories import item_repo, rule_repo
from pepper.services import cascade_service, priority_service, schedule_service


def _event(conn, title, start, end, **kw):
    item = schedule_service.add_event(conn, title=title, start_time=start, end_time=end, **kw)
    priority_service.recompute_scores(conn, item.id)
    return item


def test_reflow_shifts_lower_priority_off_an_overlap(conn):
    high = _event(conn, "CEO review", "2026-06-09T14:00:00+00:00", "2026-06-09T15:00:00+00:00",
                  commitment="promise_to_others", stakes="one_shot")
    low = _event(conn, "Gym", "2026-06-09T14:30:00+00:00", "2026-06-09T15:30:00+00:00")
    # A captured event defaults to fixed_time (an anchor). Make the gym a low-rigidity,
    # low-stakes personal item so the cascade may move it around the CEO anchor.
    item_repo.set_factors(conn, low.id, temporal_class="anytime", stakes="trivial_repeatable")
    priority_service.recompute_scores(conn, low.id)
    result = cascade_service.reflow(conn, day="2026-06-09")
    assert result.action in ("apply", "escalate")
    refreshed_low = item_repo.get_item(conn, low.id)
    refreshed_high = item_repo.get_item(conn, high.id)
    assert refreshed_high.start_time == "2026-06-09T14:00:00+00:00"  # high-P anchor unmoved
    assert refreshed_low.start_time != "2026-06-09T14:30:00+00:00"   # low-P reflowed


def test_no_before_rule_lifts_reflowed_placement(conn):
    # A global no_before rule at 10:00 must lift a relocated movable item's start.
    _event(conn, "CEO review", "2026-06-09T14:00:00+00:00", "2026-06-09T15:00:00+00:00",
           commitment="promise_to_others", stakes="one_shot")
    low = _event(conn, "Gym", "2026-06-09T14:30:00+00:00", "2026-06-09T15:30:00+00:00")
    item_repo.set_factors(conn, low.id, temporal_class="anytime", stakes="trivial_repeatable")
    priority_service.recompute_scores(conn, low.id)
    rule_repo.add(conn, kind="no_before", target_type_id=None, param="10:00")

    result = cascade_service.reflow(conn, day="2026-06-09")
    assert result.action in ("apply", "escalate")
    refreshed_low = item_repo.get_item(conn, low.id)
    # Relocated; new start respects the 10:00 (== "10:00") floor.
    assert refreshed_low.start_time >= "2026-06-09T10:00:00+00:00"


def test_delay_item_triggers_reflow(conn):
    _event(conn, "Roadmap", "2026-06-09T10:00:00+00:00", "2026-06-09T11:00:00+00:00")
    later = _event(conn, "Call", "2026-06-09T11:00:00+00:00", "2026-06-09T11:30:00+00:00")
    result = cascade_service.delay_item(conn, later.id, minutes=0, day="2026-06-09")
    assert result.action in ("apply", "escalate", "noop")


def test_delay_item_missing_id_raises(conn):
    with pytest.raises(ValueError, match="item 99999 not found"):
        cascade_service.delay_item(conn, 99999, minutes=30, day="2026-06-09")


def test_reschedule_missing_id_raises(conn):
    with pytest.raises(ValueError, match="item 99999 not found"):
        cascade_service.reschedule(
            conn, 99999,
            "2026-06-09T12:00:00+00:00", "2026-06-09T13:00:00+00:00",
            day="2026-06-09",
        )


def test_reschedule_moves_item_and_reflows(conn):
    item = _event(conn, "Standup", "2026-06-09T09:00:00+00:00", "2026-06-09T09:30:00+00:00")
    result = cascade_service.reschedule(
        conn, item.id,
        "2026-06-09T10:00:00+00:00", "2026-06-09T10:30:00+00:00",
        day="2026-06-09",
    )
    assert result.action in ("apply", "escalate", "noop")
    refreshed = item_repo.get_item(conn, item.id)
    assert refreshed.start_time == "2026-06-09T10:00:00+00:00"


def test_reflow_excludes_dropped_item(conn):
    # Two overlapping active events drive a reflow; a third already-dropped item
    # must not be re-ingested as a movable block (no re-place, no version bump).
    _event(conn, "CEO review", "2026-06-09T14:00:00+00:00", "2026-06-09T15:00:00+00:00",
                  commitment="promise_to_others", stakes="one_shot")
    low = _event(conn, "Gym", "2026-06-09T14:30:00+00:00", "2026-06-09T15:30:00+00:00")
    item_repo.set_factors(conn, low.id, temporal_class="anytime", stakes="trivial_repeatable")
    priority_service.recompute_scores(conn, low.id)
    dropped = _event(conn, "Old errand", "2026-06-09T14:15:00+00:00", "2026-06-09T14:45:00+00:00")
    item_repo.set_status(conn, dropped.id, "dropped")
    before = item_repo.get_item(conn, dropped.id)

    result = cascade_service.reflow(conn, day="2026-06-09")
    assert result.action in ("apply", "escalate")
    assert dropped.id not in result.moved

    after = item_repo.get_item(conn, dropped.id)
    assert after.start_time == before.start_time
    assert after.end_time == before.end_time
    assert after.version == before.version  # not re-touched
    assert after.status == "dropped"


def test_reflow_excludes_done_item(conn):
    # A completed item is history; it must not participate in reflow.
    _event(conn, "CEO review", "2026-06-09T14:00:00+00:00", "2026-06-09T15:00:00+00:00",
                  commitment="promise_to_others", stakes="one_shot")
    low = _event(conn, "Gym", "2026-06-09T14:30:00+00:00", "2026-06-09T15:30:00+00:00")
    item_repo.set_factors(conn, low.id, temporal_class="anytime", stakes="trivial_repeatable")
    priority_service.recompute_scores(conn, low.id)
    done = _event(conn, "Finished call", "2026-06-09T14:15:00+00:00", "2026-06-09T14:45:00+00:00")
    item_repo.set_status(conn, done.id, "done")
    before = item_repo.get_item(conn, done.id)

    result = cascade_service.reflow(conn, day="2026-06-09")
    assert result.action in ("apply", "escalate")
    assert done.id not in result.moved

    after = item_repo.get_item(conn, done.id)
    assert after.start_time == before.start_time
    assert after.end_time == before.end_time
    assert after.version == before.version
    assert after.status == "done"


def _block(item_id, start, end, *, min_duration=None, divisible=False):
    return Block(
        id=item_id, start=start, end=end,
        min_duration=min_duration if min_duration is not None else end - start,
        rigidity=0.4, protection=0.5, location=None, divisible=divisible,
        earliest=0, latest=24 * 60, anchor=False,
    )


def test_apply_surfaces_split_deferral(conn):
    # A divisible 60-min item placed as a 30-min head with 30 min deferred.
    item = _event(conn, "Deep work", "2026-06-09T10:00:00+00:00", "2026-06-09T11:00:00+00:00")
    base = cascade_service.parse_iso("2026-06-09T00:00:00+00:00")
    original = _block(item.id, 600, 660, min_duration=30, divisible=True)
    head = _block(item.id, 600, 630, min_duration=30, divisible=True)
    solution = Solution(
        placed=[head], anchors=[], dropped=[],
        deferred={item.id: 30}, cost=0.0, levers={item.id: "split"},
    )
    moved = cascade_service._apply(conn, base, [original], solution)
    assert item.id in moved
    assert "30min deferred" in moved[item.id]


def test_apply_persists_changed_duration(conn):
    # A compress lever shrinks the block; duration_estimate must follow so a
    # second reflow does not read a stale (larger) duration.
    item = _event(conn, "Review", "2026-06-09T10:00:00+00:00", "2026-06-09T11:00:00+00:00")
    base = cascade_service.parse_iso("2026-06-09T00:00:00+00:00")
    original = _block(item.id, 600, 660, min_duration=30)
    compressed = _block(item.id, 600, 630, min_duration=30)
    solution = Solution(
        placed=[compressed], anchors=[], dropped=[],
        deferred={}, cost=0.0, levers={item.id: "compress"},
    )
    cascade_service._apply(conn, base, [original], solution)
    refreshed = item_repo.get_item(conn, item.id)
    assert refreshed.duration_estimate == 30


def test_reschedule_rejects_non_positive_duration(conn):
    item = _event(conn, "Standup", "2026-06-09T09:00:00+00:00",
                  "2026-06-09T09:30:00+00:00")
    with pytest.raises(ValueError, match="new_end must be after new_start"):
        cascade_service.reschedule(
            conn, item.id,
            new_start="2026-06-09T11:00:00+00:00",
            new_end="2026-06-09T11:00:00+00:00",  # zero duration
            day="2026-06-09",
        )


def test_reschedule_rejects_inverted_window(conn):
    item = _event(conn, "Standup", "2026-06-09T09:00:00+00:00",
                  "2026-06-09T09:30:00+00:00")
    with pytest.raises(ValueError, match="new_end must be after new_start"):
        cascade_service.reschedule(
            conn, item.id,
            new_start="2026-06-09T12:00:00+00:00",
            new_end="2026-06-09T11:00:00+00:00",  # end before start
            day="2026-06-09",
        )


def test_cancel_item_sets_cancelled_status_without_learning(conn):
    item = _event(conn, "Dropme", "2026-06-09T09:00:00+00:00",
                  "2026-06-09T10:00:00+00:00")
    cascade_service.cancel_item(conn, item.id)
    refreshed = item_repo.get_item(conn, item.id)
    assert refreshed.status == "cancelled"
    # No learning observation was appended (cancel is a decision, not a signal).
    # observation_repo exposes no per-item reader, so count the rows directly.
    n = conn.execute(
        "SELECT COUNT(*) FROM observations WHERE item_id = ?", (item.id,)
    ).fetchone()[0]
    assert n == 0


def test_cancel_item_missing_id_raises(conn):
    with pytest.raises(ValueError, match="item 99999 not found"):
        cascade_service.cancel_item(conn, 99999)


def test_impossible_returns_conflict_report_and_no_data_loss(conn):
    # Three fixed-time anchors stacked on the same hour: genuinely unsatisfiable.
    ids = []
    for i in range(3):
        item = _event(conn, f"a{i}", "2026-06-09T09:00:00+00:00",
                      "2026-06-09T10:00:00+00:00", commitment="promise_to_others",
                      stakes="one_shot")
        ids.append(item.id)

    res = cascade_service.reflow(conn, day="2026-06-09")
    assert res.action == "impossible"
    assert res.moved == {}
    # Structured conflict report: a contested window grouping the competing items,
    # each annotated with the priority signals Hermes needs.
    assert res.conflicts, "expected a populated conflict report"
    cluster = res.conflicts[0]
    assert "window" in cluster and "start" in cluster["window"]
    assert len(cluster["items"]) == 3
    sample = cluster["items"][0]
    for key in ("item_id", "title", "start", "end", "protection", "rigidity",
                "commitment", "stakes"):
        assert key in sample
    # No item was moved or dropped.
    for item_id in ids:
        row = item_repo.get_item(conn, item_id)
        assert row.start_time == "2026-06-09T09:00:00+00:00"
        assert row.status == "scheduled"


def test_impossible_groups_two_disjoint_conflict_clusters(conn):
    # Two separate stacked-anchor pileups in the same day (09:00 and 14:00) must
    # be reported as two distinct contested clusters, not merged into one.
    for hour in ("09", "14"):
        for i in range(3):
            _event(conn, f"x{hour}_{i}",
                   f"2026-06-09T{hour}:00:00+00:00", f"2026-06-09T{hour}:30:00+00:00",
                   commitment="promise_to_others", stakes="one_shot")

    res = cascade_service.reflow(conn, day="2026-06-09")
    assert res.action == "impossible"
    assert len(res.conflicts) == 2, "two disjoint pileups must be two clusters"
    # Each cluster holds exactly its 3 competing items, and the windows are disjoint.
    assert all(len(c["items"]) == 3 for c in res.conflicts)
    windows = sorted((c["window"]["start"], c["window"]["end"]) for c in res.conflicts)
    assert windows[0][1] <= windows[1][0], "cluster windows must not overlap"


def test_escalate_returns_options_and_does_not_mutate(conn, monkeypatch):
    # Force the gate to escalate over the real solver output so we exercise the
    # no-auto-apply path. An anchor + an overlapping movable yields >=1 real
    # Solution whose described moves we can assert on.
    from pepper.cascade.gate import GateDecision
    _event(conn, "CEO review", "2026-06-09T14:00:00+00:00",
           "2026-06-09T15:00:00+00:00", commitment="promise_to_others", stakes="one_shot")
    gym = _event(conn, "Gym", "2026-06-09T14:30:00+00:00", "2026-06-09T15:30:00+00:00")
    item_repo.set_factors(conn, gym.id, temporal_class="anytime", stakes="trivial_repeatable")
    priority_service.recompute_scores(conn, gym.id)

    def fake_decide(solutions, *args, **kwargs):
        return GateDecision("escalate", None, solutions)
    monkeypatch.setattr(cascade_service, "decide", fake_decide)

    res = cascade_service.reflow(conn, day="2026-06-09")
    assert res.action == "escalate"
    assert res.moved == {}                      # nothing auto-applied
    assert res.options                          # at least one described option
    assert "cost" in res.options[0] and "moves" in res.options[0]
    # The schedule was NOT mutated — the movable still sits at its original time.
    assert item_repo.get_item(conn, gym.id).start_time == "2026-06-09T14:30:00+00:00"
