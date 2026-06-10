from pepper.repositories import observation_repo
from pepper.repositories import vector_repo


def test_append_is_immutable_and_listable(conn):
    t = vector_repo.create_type(conn, "standup")
    observation_repo.append(
        conn, type_id=t, item_id=1, estimated=30, actual=46,
        scheduled_start="2026-06-07T09:00:00+00:00", outcome="done",
    )
    observation_repo.append(
        conn, type_id=t, item_id=2, estimated=30, actual=44,
        scheduled_start="2026-06-08T09:00:00+00:00", outcome="done",
    )
    rows = observation_repo.list_by_type(conn, t)
    assert [r.actual for r in rows] == [46, 44]
    assert rows[0].day_of_week is not None  # derived from scheduled_start


def test_list_by_type_empty(conn):
    assert observation_repo.list_by_type(conn, 999) == []
