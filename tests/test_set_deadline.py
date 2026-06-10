import pytest

from pepper.repositories import goal_repo, item_repo
from pepper.services import planner_service, schedule_service


def test_set_deadline_missing_item_raises(conn):
    with pytest.raises(ValueError):
        planner_service.set_deadline(conn, 99999, deadline="2026-06-12T17:00:00+00:00",
                                     effort_minutes=360)


def test_set_deadline_sets_fields_and_creates_goal(conn):
    item = schedule_service.add_task(conn, title="Q3 roadmap", duration_estimate=60,
                                     divisibility="divisible")
    planner_service.set_deadline(conn, item.id, deadline="2026-06-12T17:00:00+00:00",
                                 effort_minutes=360, total_scope=4)
    refreshed = item_repo.get_item(conn, item.id)
    assert refreshed.deadline == "2026-06-12T17:00:00+00:00"
    assert refreshed.effort_estimate == 360
    assert refreshed.temporal_class == "deadline"
    goal = goal_repo.get_for_item(conn, item.id)
    assert goal.total_scope == 4
