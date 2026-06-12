import pytest

from pepper.learning import habits
from pepper.repositories import item_repo, observation_repo, type_stats_repo, vector_repo
from pepper.services import schedule_service, suggestion_service

DAY = "2026-06-15"


def _busy(conn, title, start_hm, end_hm):
    return schedule_service.add_event(
        conn, title=title,
        start_time=f"{DAY}T{start_hm}:00+00:00", end_time=f"{DAY}T{end_hm}:00+00:00",
    )


def _observe_done(conn, type_id, start_iso, minutes=60):
    observation_repo.append(conn, type_id=type_id, item_id=None, estimated=minutes,
                            actual=minutes, outcome="done", scheduled_start=start_iso)


def test_tod_affinity_shares_and_empty():
    assert habits.tod_affinity([]) == {}

    class Obs:
        def __init__(self, tod, outcome="done"):
            self.time_of_day = tod
            self.outcome = outcome

    obs = [Obs("evening"), Obs("evening"), Obs("morning"),
           Obs("evening", outcome="dropped_pressure"), Obs(None)]
    aff = habits.tod_affinity(obs)
    assert aff == {"evening": 2 / 3, "morning": 1 / 3}


def test_tod_bucket_matches_observation_bucketing():
    # must stay in lockstep with observation_repo._tod_bucket
    for hour in range(24):
        assert habits.tod_bucket(hour) == observation_repo._tod_bucket(hour)


def test_unknown_item_raises(conn):
    with pytest.raises(ValueError):
        suggestion_service.suggest_slots(conn, 999, DAY)


def test_untyped_task_books_duration_chronological(conn):
    task = schedule_service.add_task(conn, title="mystery chore", duration_estimate=45)
    out = suggestion_service.suggest_slots(conn, task.id, DAY)
    assert out["duration_minutes"] == 45
    assert out["duration_source"] == "booked"
    assert len(out["options"]) > 0
    first = out["options"][0]
    assert first["start"] == "2026-06-15T09:00:00+00:00"
    assert first["habit_score"] is None
    starts = [o["start"] for o in out["options"]]
    assert starts == sorted(starts)


def test_habit_ranking_prefers_learned_bucket(conn):
    type_id = vector_repo.create_type(conn, "gym")
    for d in ("08", "09", "10"):
        _observe_done(conn, type_id, f"2026-06-{d}T18:00:00+00:00")
    task = schedule_service.add_task(conn, title="gym session", duration_estimate=60)
    item_repo.set_type(conn, task.id, type_id)
    # split the day so morning, afternoon and evening slots all exist
    _busy(conn, "block-noon", "12:00", "13:00")
    _busy(conn, "block-late", "16:00", "17:00")
    out = suggestion_service.suggest_slots(conn, task.id, DAY)
    assert out["options"][0]["time_of_day"] == "evening"
    assert out["options"][0]["habit_score"] == 1.0


def test_confident_type_stats_drive_duration(conn):
    type_id = vector_repo.create_type(conn, "deep_work")
    type_stats_repo.upsert(conn, type_id, avg_actual=90.0, confidence=0.9, sample_count=10)
    task = schedule_service.add_task(conn, title="write design doc", duration_estimate=30)
    item_repo.set_type(conn, task.id, type_id)
    out = suggestion_service.suggest_slots(conn, task.id, DAY)
    assert out["duration_minutes"] == 90
    assert out["duration_source"] == "learned"
    first = out["options"][0]
    assert first["end"] == "2026-06-15T10:30:00+00:00"  # 09:00 + 90min


def test_slots_too_small_filtered(conn):
    # 12:30-13:00 gap is 30min (too small); 14:00-17:00 fits
    _busy(conn, "am", "09:00", "12:30")
    _busy(conn, "pm", "13:00", "14:00")
    _busy(conn, "late", "17:00", "18:00")
    task = schedule_service.add_task(conn, title="long task", duration_estimate=60)
    out = suggestion_service.suggest_slots(conn, task.id, DAY)
    starts = [o["start"] for o in out["options"]]
    assert "2026-06-15T12:30:00+00:00" not in starts  # 30min gap dropped
    assert "2026-06-15T14:00:00+00:00" in starts


def test_max_three_options(conn):
    for hm in (("10:00", "10:15"), ("11:00", "11:15"), ("13:00", "13:15"), ("15:00", "15:15")):
        _busy(conn, "wall", *hm)
    task = schedule_service.add_task(conn, title="tiny", duration_estimate=15)
    out = suggestion_service.suggest_slots(conn, task.id, DAY)
    assert len(out["options"]) == 3


def test_suggest_slot_tool_envelope(conn):
    from pepper.mcp.server import pepper_add_task, pepper_suggest_slot
    added = pepper_add_task(title="plan trip", duration_estimate=40)
    out = pepper_suggest_slot(added["data"]["id"], DAY)
    assert out["success"] is True
    assert out["data"]["duration_minutes"] == 40
    bad = pepper_suggest_slot(99999, DAY)
    assert bad["success"] is False
