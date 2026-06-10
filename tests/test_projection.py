from pepper.planner.projection import project
from pepper.services import planner_service, schedule_service


def test_project_flags_at_risk_when_effort_exceeds_capacity(conn):
    item = schedule_service.add_task(conn, title="big", duration_estimate=60,
                                     divisibility="divisible")
    # 600 min of effort but only a short window before the deadline
    planner_service.set_deadline(conn, item.id, deadline="2026-06-09T11:00:00+00:00",
                                 effort_minutes=600)
    p = project(conn, item.id, from_day="2026-06-09", day_start_min=540, day_end_min=600)
    assert p.status == "at_risk"
    assert p.remaining_effort == 600


def test_project_on_track_with_ample_capacity(conn):
    item = schedule_service.add_task(conn, title="small", duration_estimate=60,
                                     divisibility="divisible")
    planner_service.set_deadline(conn, item.id, deadline="2026-06-16T17:00:00+00:00",
                                 effort_minutes=120)
    p = project(conn, item.id, from_day="2026-06-09", day_start_min=540, day_end_min=1020)
    assert p.status == "on_track"
