from pepper.planner.slots import free_slots
from pepper.repositories import item_repo
from pepper.services import schedule_service


def test_free_slots_ignores_non_active_items(conn):
    item = schedule_service.add_event(conn, title="Cancelled",
                                      start_time="2026-06-09T09:00:00+00:00",
                                      end_time="2026-06-09T12:00:00+00:00")
    item_repo.set_status(conn, item.id, "cancelled")
    slots = free_slots(conn, "2026-06-09", day_start_min=540, day_end_min=1020, min_minutes=60)
    # 09:00 == 540 must be free; the cancelled block must not carve out 09:00-12:00
    assert any(s.start == "2026-06-09T09:00:00+00:00" for s in slots)


def test_free_slots_finds_gap_between_events(conn):
    schedule_service.add_event(conn, title="A", start_time="2026-06-09T09:00:00+00:00",
                               end_time="2026-06-09T10:00:00+00:00")
    schedule_service.add_event(conn, title="B", start_time="2026-06-09T14:00:00+00:00",
                               end_time="2026-06-09T15:00:00+00:00")
    slots = free_slots(conn, "2026-06-09", day_start_min=540, day_end_min=1020, min_minutes=60)
    # gap 10:00-14:00 (240 min) must appear
    assert any(s.minutes == 240 for s in slots)
