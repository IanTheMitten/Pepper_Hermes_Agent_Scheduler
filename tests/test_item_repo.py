from pepper.repositories import item_repo


def _add_event(conn, title, start, end):
    return item_repo.add_item(
        conn,
        title=title,
        start_time=start,
        end_time=end,
        duration_estimate=30,
        min_duration=30,
        temporal_class="fixed_time",
    )


def test_add_then_get_roundtrips(conn):
    item_id = _add_event(conn, "Standup", "2026-06-07T09:00:00+00:00", "2026-06-07T09:30:00+00:00")
    item = item_repo.get_item(conn, item_id)
    assert item is not None
    assert item.title == "Standup"
    assert item.version == 1
    assert item.status == "scheduled"


def test_get_missing_returns_none(conn):
    assert item_repo.get_item(conn, 999) is None


def test_list_in_range_returns_overlapping_ordered(conn):
    _add_event(conn, "B", "2026-06-07T11:00:00+00:00", "2026-06-07T12:00:00+00:00")
    _add_event(conn, "A", "2026-06-07T09:00:00+00:00", "2026-06-07T10:00:00+00:00")
    items = item_repo.list_in_range(
        conn, "2026-06-07T00:00:00+00:00", "2026-06-08T00:00:00+00:00"
    )
    assert [i.title for i in items] == ["A", "B"]


def test_list_in_range_excludes_outside_and_unscheduled(conn):
    _add_event(conn, "In", "2026-06-07T09:00:00+00:00", "2026-06-07T10:00:00+00:00")
    _add_event(conn, "Out", "2026-06-09T09:00:00+00:00", "2026-06-09T10:00:00+00:00")
    item_repo.add_item(  # unscheduled task: no start/end
        conn, title="Task", start_time=None, end_time=None,
        duration_estimate=60, min_duration=60, temporal_class="anytime",
    )
    items = item_repo.list_in_range(
        conn, "2026-06-07T00:00:00+00:00", "2026-06-08T00:00:00+00:00"
    )
    assert [i.title for i in items] == ["In"]
