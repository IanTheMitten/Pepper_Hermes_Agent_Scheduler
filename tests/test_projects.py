from pepper.repositories import item_repo, project_repo
from pepper.services import planner_service, schedule_service


def test_project_rollup_sums_member_effort(conn):
    pid = project_repo.create(conn, "Launch", deadline="2026-06-20T17:00:00+00:00")
    a = schedule_service.add_task(conn, title="copy", duration_estimate=60)
    b = schedule_service.add_task(conn, title="art", duration_estimate=60)
    for t in (a, b):
        item_repo.set_deadline_fields(conn, t.id, "2026-06-20T17:00:00+00:00", 120)
        item_repo.set_project(conn, t.id, pid)
    rollup = planner_service.project_rollup(conn, pid, from_day="2026-06-09")
    assert rollup.remaining_effort == 240
    assert rollup.status in ("on_track", "at_risk")
