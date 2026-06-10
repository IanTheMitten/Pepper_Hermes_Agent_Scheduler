from pepper.planner.allocation import allocate_sessions
from pepper.repositories import item_repo
from pepper.services import planner_service, schedule_service


def test_allocate_reserves_sessions_covering_effort(conn):
    item = schedule_service.add_task(conn, title="roadmap", duration_estimate=60,
                                     divisibility="divisible")
    planner_service.set_deadline(conn, item.id, deadline="2026-06-11T17:00:00+00:00",
                                 effort_minutes=180)
    reserved = allocate_sessions(conn, item.id, from_day="2026-06-09",
                                 session_minutes=60, day_start_min=540, day_end_min=1020)
    assert sum(r.minutes for r in reserved) >= 180
    # each reserved session is a real auto_reserved child item
    children = item_repo.list_in_range(conn, "2026-06-09T00:00:00+00:00",
                                       "2026-06-12T00:00:00+00:00")
    assert any(c.parent_item_id == item.id for c in children)


def test_allocate_fills_large_gap_with_multiple_sessions(conn):
    item = schedule_service.add_task(conn, title="big project", duration_estimate=60,
                                     divisibility="divisible")
    planner_service.set_deadline(conn, item.id, deadline="2026-06-11T17:00:00+00:00",
                                 effort_minutes=300)
    # single mostly-empty day window: 540..1020 == 480 minutes
    reserved = allocate_sessions(conn, item.id, from_day="2026-06-09",
                                 session_minutes=60, day_start_min=540, day_end_min=1020)
    # multiple back-to-back sessions, covering the full effort
    assert len(reserved) > 1
    assert sum(r.minutes for r in reserved) >= 300
    # sessions do not overlap each other
    ordered = sorted(reserved, key=lambda r: r.start)
    for a, b in zip(ordered, ordered[1:]):
        assert a.end <= b.start
