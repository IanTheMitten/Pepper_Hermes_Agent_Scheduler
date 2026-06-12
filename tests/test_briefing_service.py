from pepper.repositories import item_repo, type_stats_repo, vector_repo
from pepper.services import briefing_service, planner_service, schedule_service

DAY = "2026-06-15"


def _event(conn, title, start_hm, end_hm, **kw):
    return schedule_service.add_event(
        conn, title=title,
        start_time=f"{DAY}T{start_hm}:00+00:00", end_time=f"{DAY}T{end_hm}:00+00:00", **kw,
    )


def test_empty_day_briefing(conn):
    b = briefing_service.build_briefing(conn, DAY)
    assert b["schedule"] == []
    assert b["overlaps"] == []
    assert b["at_risk"] == []
    assert b["estimate_drift"] == []
    assert b["unscheduled_deadlines"] == []


def test_schedule_lists_only_active_items(conn):
    kept = _event(conn, "standup", "09:00", "09:30")
    dropped = _event(conn, "gym", "10:00", "11:00")
    item_repo.set_status(conn, dropped.id, "cancelled")
    b = briefing_service.build_briefing(conn, DAY)
    assert [i["id"] for i in b["schedule"]] == [kept.id]


def test_overlaps_detected(conn):
    a = _event(conn, "review", "10:00", "11:00")
    c = _event(conn, "call", "10:30", "11:30")
    _event(conn, "lunch", "12:00", "13:00")
    b = briefing_service.build_briefing(conn, DAY)
    assert b["overlaps"] == [{"item_ids": [a.id, c.id], "titles": ["review", "call"]}]


def test_at_risk_deadline_surfaces(conn):
    # 9h-18h window fully busy on the only day before the deadline -> no capacity
    _event(conn, "offsite", "09:00", "18:00")
    task = schedule_service.add_task(conn, title="big report", duration_estimate=120)
    planner_service.set_deadline(conn, task.id, deadline="2026-06-16T00:00:00+00:00",
                                 effort_minutes=120)
    b = briefing_service.build_briefing(conn, DAY)
    assert len(b["at_risk"]) == 1
    risk = b["at_risk"][0]
    assert risk["item_id"] == task.id
    assert risk["remaining_effort"] == 120
    assert risk["free_capacity"] == 0


def test_on_track_deadline_not_flagged(conn):
    task = schedule_service.add_task(conn, title="small note", duration_estimate=30)
    planner_service.set_deadline(conn, task.id, deadline="2026-06-20T00:00:00+00:00",
                                 effort_minutes=30)
    b = briefing_service.build_briefing(conn, DAY)
    assert b["at_risk"] == []


def test_estimate_drift_warns_on_confident_divergence(conn):
    type_id = vector_repo.create_type(conn, "deep_work")
    type_stats_repo.upsert(conn, type_id, avg_actual=90.0, confidence=0.8, sample_count=10)
    item = _event(conn, "write spec", "09:00", "10:00")  # booked 60, learned 90
    item_repo.set_type(conn, item.id, type_id)
    b = briefing_service.build_briefing(conn, DAY)
    assert b["estimate_drift"] == [{
        "item_id": item.id, "title": "write spec",
        "booked_minutes": 60, "learned_minutes": 90,
    }]


def test_estimate_drift_silent_when_unconfident_or_close(conn):
    low_conf = vector_repo.create_type(conn, "errand")
    type_stats_repo.upsert(conn, low_conf, avg_actual=90.0, confidence=0.2, sample_count=1)
    close = vector_repo.create_type(conn, "standup")
    type_stats_repo.upsert(conn, close, avg_actual=65.0, confidence=0.9, sample_count=10)
    a = _event(conn, "post office", "09:00", "10:00")
    item_repo.set_type(conn, a.id, low_conf)
    c = _event(conn, "sync", "11:00", "12:00")
    item_repo.set_type(conn, c.id, close)
    b = briefing_service.build_briefing(conn, DAY)
    assert b["estimate_drift"] == []


def test_unscheduled_deadline_within_lookahead(conn):
    soon = schedule_service.add_task(conn, title="taxes", duration_estimate=60,
                                     deadline="2026-06-18T00:00:00+00:00")
    schedule_service.add_task(conn, title="far off", duration_estimate=60,
                              deadline="2026-07-30T00:00:00+00:00")
    no_deadline = schedule_service.add_task(conn, title="someday", duration_estimate=60)
    assert no_deadline.deadline is None
    b = briefing_service.build_briefing(conn, DAY)
    assert [t["item_id"] for t in b["unscheduled_deadlines"]] == [soon.id]
    assert b["unscheduled_deadlines"][0]["deadline"] == "2026-06-18T00:00:00+00:00"


def test_briefing_tool_envelope(conn):
    from pepper.mcp.server import pepper_briefing
    out = pepper_briefing(DAY)
    assert out["success"] is True
    assert out["error"] is None
    assert set(out["data"]) == {"schedule", "overlaps", "at_risk",
                                "estimate_drift", "unscheduled_deadlines"}
