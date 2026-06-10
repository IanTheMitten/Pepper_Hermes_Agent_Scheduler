from pepper.integration import hermes
from pepper.repositories import travel_repo, type_stats_repo, vector_repo
from pepper.services import reminder_service, schedule_service


def test_schedule_creates_cron_jobs_travel_aware(conn):
    t = vector_repo.create_type(conn, "standup")
    type_stats_repo.upsert(conn, t, avg_start_slip=0.0, sample_count=5, confidence=0.7)
    travel_repo.put(conn, "Home", "Office", 25, source="manual")
    item = schedule_service.add_event(
        conn, title="standup", start_time="2026-06-09T09:00:00+00:00",
        end_time="2026-06-09T09:30:00+00:00", location="Office",
    )
    from pepper.repositories import item_repo
    item_repo.set_type(conn, item.id, t)
    cron = hermes.FakeCron()
    reminder_service.schedule_item_reminders(conn, item.id, cron, here="Home")
    # warning (travel-aware), 1-min app push, completion check => 3 jobs
    assert len(cron.jobs) == 3
    # travel-aware leave-now fires 30 min before (25 travel + 5 prep)
    assert any(j[1] == "2026-06-09T08:30:00+00:00" for j in cron.jobs)


def test_no_completion_plan_when_end_time_missing(conn):
    from pepper.repositories import item_repo
    item = schedule_service.add_task(conn, title="write report", duration_estimate=60)
    item_repo.set_times(conn, item.id, "2026-06-09T09:00:00+00:00", None)
    cron = hermes.FakeCron()
    reminder_service.schedule_item_reminders(conn, item.id, cron)
    # only warning + 1-min app push; no completion check (end_time is None)
    assert len(cron.jobs) == 2
    assert all(j[1] is not None for j in cron.jobs)


def test_fire_sends_via_gateway(conn):
    gw = hermes.FakeGateway()
    reminder_service.fire("You have standup in 5 minutes.", gw)
    assert gw.sent == ["You have standup in 5 minutes."]
