from pepper.repositories import item_repo, objective_repo
from pepper.services import priority_service, schedule_service
from pepper.services.priority_service import _day_load


def test_active_objective_raises_protection_score(conn):
    t = 7
    item = schedule_service.add_task(conn, title="deep work", duration_estimate=90,
                                     stakes="reschedulable")
    item_repo.set_type(conn, item.id, t)
    base_then = priority_service.recompute_with_context(conn, item.id, day="2026-06-09")
    objective_repo.create(conn, "Protect deep work", target_type_id=t, weight=1.25)
    raised = priority_service.recompute_with_context(conn, item.id, day="2026-06-09")
    assert raised > base_then  # objective nudged protection up, still bounded


def test_day_load_ignores_non_active_items(conn):
    day = "2026-06-09"
    keep = schedule_service.add_event(
        conn, title="standup", start_time=f"{day}T09:00:00+00:00",
        end_time=f"{day}T09:30:00+00:00")
    big = schedule_service.add_event(
        conn, title="all-hands", start_time=f"{day}T10:00:00+00:00",
        end_time=f"{day}T16:00:00+00:00")
    with_both = _day_load(conn, day)
    item_repo.set_status(conn, big.id, "dropped")
    after_drop = _day_load(conn, day)
    # dropping a large item must lower the day's load, not leave it counted
    assert after_drop < with_both
    # equals a day that only ever had the active item
    item_repo.set_status(conn, keep.id, "scheduled")
    assert after_drop == _day_load(conn, day)
