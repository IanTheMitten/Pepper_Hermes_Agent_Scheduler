from pepper.mcp.server import pepper_add_recurrence, pepper_edit_recurrence
from pepper.recurrence.materializer import edit_all, materialize
from pepper.repositories import item_repo, recurrence_repo, vector_repo
from pepper.services import schedule_service  # noqa: F401 (ensures schema loaded)


def test_materialize_creates_pretrusted_instances(conn):
    standup = vector_repo.create_type(conn, "standup")
    rid = recurrence_repo.create(
        conn, title="Standup", type_id=standup, freq="weekly", interval=1, byday="MO,TU,WE,TH,FR",
        at_time="09:00", duration_estimate=15, until=None, location="Office",
        commitment="promise_to_others", counterparty_id=None, temporal_class="fixed_time",
        stakes="reschedulable", divisibility="atomic",
    )
    created = materialize(conn, rid, horizon_days=6, today_iso="2026-06-08")  # Mon..Sun
    assert len(created) == 5  # Mon-Fri (Sat/Sun excluded; next Mon is beyond the horizon)
    from pepper.repositories import item_repo
    instances = item_repo.list_in_range(conn, "2026-06-08T00:00:00+00:00",
                                        "2026-06-15T00:00:00+00:00")
    assert all(i.series_id == rid for i in instances)
    assert all(i.type_id == standup for i in instances)  # pre-trusted: inherited, not classified


def test_materialize_is_idempotent_via_watermark(conn):
    rid = recurrence_repo.create(
        conn, title="Daily", type_id=None, freq="daily", interval=1, byday=None,
        at_time="09:00", duration_estimate=30, until=None, location=None,
        commitment="solo", counterparty_id=None, temporal_class="fixed_time",
        stakes="reschedulable", divisibility="atomic",
    )
    materialize(conn, rid, horizon_days=4, today_iso="2026-06-08")
    # Same today + horizon again: the watermark must prevent re-materializing
    # any day already covered. (The tail may extend a few days because the
    # horizon is relative to watermark+1, so assert per-day uniqueness instead
    # of exactly-zero.)
    materialize(conn, rid, horizon_days=4, today_iso="2026-06-08")
    instances = item_repo.list_in_range(conn, "2026-06-01T00:00:00+00:00",
                                        "2026-07-01T00:00:00+00:00")
    days = [i.start_time[:10] for i in instances]
    assert len(days) == len(set(days)), f"duplicate days materialized: {sorted(days)}"


def test_add_recurrence_rejects_unknown_freq(conn):
    out = pepper_add_recurrence(
        title="Bad", freq="fortnightly", at_time="09:00", duration_estimate=30,
    )
    assert out["success"] is False
    assert out["error"] is not None


def test_edit_one_detaches_single_instance_only(conn):
    standup = vector_repo.create_type(conn, "standup")
    rid = recurrence_repo.create(
        conn, title="Standup", type_id=standup, freq="daily", interval=1, byday=None,
        at_time="09:00", duration_estimate=15, until=None, location="Office",
        commitment="solo", counterparty_id=None, temporal_class="fixed_time",
        stakes="reschedulable", divisibility="atomic",
    )
    created = materialize(conn, rid, horizon_days=3, today_iso="2026-06-08")
    item_repo.set_detached(conn, created[1])
    # edit_all regenerates the non-detached tail; the detached instance survives untouched
    edit_all(conn, rid, today_iso="2026-06-08", changes={"at_time": "10:00"},
             horizon_days=3)
    survivor = item_repo.get_item(conn, created[1])
    assert survivor is not None and survivor.detached == 1
    assert survivor.start_time.endswith("09:00:00+00:00")  # original time kept

    # today's instance (created[0], 2026-06-08) is preserved untouched with the old time
    today_inst = item_repo.get_item(conn, created[0])
    assert today_inst is not None
    assert today_inst.start_time.endswith("09:00:00+00:00")  # today kept at old time

    # the regenerated tail (strictly after today and after the detached 06-09)
    # reflects the new template at 10:00
    tail = item_repo.list_in_range(conn, "2026-06-10T00:00:00+00:00",
                                   "2026-06-12T00:00:00+00:00")
    new_template = [i for i in tail if i.detached == 0
                    and i.start_time.endswith("10:00:00+00:00")]
    assert new_template, "regenerated tail should carry the new 10:00 template"


def test_edit_recurrence_rejects_unknown_scope(conn):
    rid = recurrence_repo.create(
        conn, title="Daily", type_id=None, freq="daily", interval=1, byday=None,
        at_time="09:00", duration_estimate=30, until=None, location=None,
        commitment="solo", counterparty_id=None, temporal_class="fixed_time",
        stakes="reschedulable", divisibility="atomic",
    )
    out = pepper_edit_recurrence(recurrence_id=rid, scope="bogus")
    assert out["success"] is False
    assert out["error"] is not None
