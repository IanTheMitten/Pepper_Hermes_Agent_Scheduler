from pepper.domain.item import Stakes
from pepper.mcp.server import pepper_resolve_person, pepper_set_priority_factors
from pepper.repositories import item_repo, person_repo
from pepper.services import priority_service, schedule_service


def test_recompute_writes_scores_from_factors(conn):
    sam = person_repo.create(conn, "Sam", counterparty_weight="high", weight_source="user_set")
    item = schedule_service.add_event(
        conn, title="Anniversary dinner",
        start_time="2026-06-07T19:30:00+00:00", end_time="2026-06-07T21:00:00+00:00",
        commitment="promise_to_others", counterparty_id=sam, stakes="one_shot",
    )
    priority_service.recompute_scores(conn, item.id)
    updated = item_repo.get_item(conn, item.id)
    assert updated.protection_score == 1.0   # partner + one_shot
    assert updated.rigidity_score == 0.9     # fixed_time event


def test_set_factors_then_recompute(conn):
    item = schedule_service.add_task(conn, title="Report", duration_estimate=120,
                                     deadline="2026-06-10T17:00:00+00:00")
    item_repo.set_factors(conn, item.id, stakes="one_shot")
    priority_service.recompute_scores(conn, item.id)
    assert item_repo.get_item(conn, item.id).protection_score > 0.0


def test_resolve_person_creates_when_new(conn):
    out = pepper_resolve_person(name="Boss", relationship="manager", counterparty_weight="high")
    assert out["success"] is True
    assert out["data"]["status"] in ("created", "found")
    assert out["data"]["person_id"] is not None


def test_set_priority_factors_tool_recomputes(conn):
    item = schedule_service.add_task(conn, title="Slides", duration_estimate=60)
    res = pepper_set_priority_factors(item_id=item.id, stakes="one_shot",
                                      commitment="promise_to_others")
    assert res["success"] is True
    assert item_repo.get_item(conn, item.id).protection_score > 0.0


def test_set_factors_normalizes_enum_values(conn):
    # Passing an (str, Enum) member must store its .value, satisfying the CHECK constraint.
    item = schedule_service.add_task(conn, title="X", duration_estimate=30)
    item_repo.set_factors(conn, item.id, stakes=Stakes.one_shot)
    assert item_repo.get_item(conn, item.id).stakes == "one_shot"
