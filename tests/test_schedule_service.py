import pytest

from pepper.services import schedule_service


def test_add_event_computes_duration_and_persists(conn):
    item = schedule_service.add_event(
        conn,
        title="Board meeting",
        start_time="2026-06-07T15:00:00+00:00",
        end_time="2026-06-07T16:00:00+00:00",
        location="HQ",
    )
    assert item.id > 0
    assert item.duration_estimate == 60
    assert item.temporal_class == "fixed_time"
    assert item.location == "HQ"


def test_add_event_rejects_non_positive_duration(conn):
    with pytest.raises(ValueError):
        schedule_service.add_event(
            conn,
            title="Bad",
            start_time="2026-06-07T16:00:00+00:00",
            end_time="2026-06-07T15:00:00+00:00",
        )


def test_add_task_is_unscheduled_with_temporal_class(conn):
    flexible = schedule_service.add_task(conn, title="Write report", duration_estimate=90)
    assert flexible.start_time is None
    assert flexible.temporal_class == "anytime"

    due = schedule_service.add_task(
        conn, title="File taxes", duration_estimate=120, deadline="2026-06-10T17:00:00+00:00"
    )
    assert due.temporal_class == "deadline"
    assert due.deadline == "2026-06-10T17:00:00+00:00"


def test_get_schedule_returns_events_in_range_only(conn):
    schedule_service.add_event(
        conn, title="In", start_time="2026-06-07T09:00:00+00:00",
        end_time="2026-06-07T10:00:00+00:00",
    )
    schedule_service.add_task(conn, title="Flexible", duration_estimate=30)
    result = schedule_service.get_schedule(
        conn, start_time="2026-06-07T00:00:00+00:00", end_time="2026-06-08T00:00:00+00:00"
    )
    assert len(result) == 1
    assert result[0]["title"] == "In"
    assert isinstance(result[0], dict)
