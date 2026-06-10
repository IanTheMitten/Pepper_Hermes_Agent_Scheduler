from pepper.mcp.server import (
    bootstrap,
    pepper_add_event,
    pepper_add_task,
    pepper_cancel_item,
    pepper_get_schedule,
    pepper_mark_progress,
    pepper_onboard,
    pepper_reschedule,
    pepper_resolve_conflict,
    pepper_set_deadline,
    pepper_set_item_type,
)


def test_bootstrap_makes_fresh_db_usable(tmp_path, monkeypatch):
    # No `conn` fixture here: simulate a real first run against a DB that was
    # never migrated. bootstrap() must create the schema so tools work.
    monkeypatch.setenv("PEPPER_DB_PATH", str(tmp_path / "fresh.db"))
    bootstrap()
    out = pepper_add_event(
        title="First run",
        start_time="2026-06-08T09:00:00+00:00",
        end_time="2026-06-08T10:00:00+00:00",
    )
    assert out["success"] is True
    assert out["error"] is None


def test_add_event_tool_returns_success_envelope(conn):
    out = pepper_add_event(
        title="Standup",
        start_time="2026-06-07T09:00:00+00:00",
        end_time="2026-06-07T09:30:00+00:00",
    )
    assert out["success"] is True
    assert out["error"] is None
    assert out["data"]["title"] == "Standup"
    assert out["data"]["duration_estimate"] == 30


def test_add_event_tool_rejects_bad_range(conn):
    out = pepper_add_event(
        title="Bad",
        start_time="2026-06-07T10:00:00+00:00",
        end_time="2026-06-07T09:00:00+00:00",
    )
    assert out["success"] is False
    assert out["data"] is None
    assert "end_time" in out["error"]


def test_add_event_tool_rejects_unknown_enum(conn):
    out = pepper_add_event(
        title="X",
        start_time="2026-06-07T09:00:00+00:00",
        end_time="2026-06-07T10:00:00+00:00",
        stakes="catastrophic",
    )
    assert out["success"] is False


def test_get_schedule_tool_reads_back_added_items(conn):
    pepper_add_event(
        title="Standup",
        start_time="2026-06-07T09:00:00+00:00",
        end_time="2026-06-07T09:30:00+00:00",
    )
    pepper_add_task(title="Flexible thing", duration_estimate=45)
    out = pepper_get_schedule(
        start_time="2026-06-07T00:00:00+00:00", end_time="2026-06-08T00:00:00+00:00"
    )
    assert out["success"] is True
    titles = [row["title"] for row in out["data"]]
    assert titles == ["Standup"]  # the unscheduled task is excluded from range


def test_set_item_type_tool_rejects_empty_name(conn):
    out = pepper_set_item_type(item_id=1, type_name="  ", title="x")
    assert out["success"] is False


def test_set_item_type_tool_rejects_unknown_item(conn):
    out = pepper_set_item_type(item_id=9999, type_name="dog_walk", title="walk the dog")
    assert out["success"] is False


def test_mark_progress_tool_rejects_bad_outcome(conn):
    out = pepper_mark_progress(item_id=1, actual_minutes=30, outcome="exploded")
    assert out["success"] is False


def test_mark_progress_tool_rejects_nonpositive_minutes(conn):
    out = pepper_mark_progress(item_id=1, actual_minutes=0)
    assert out["success"] is False


def test_reschedule_tool_rejects_unknown_item(conn):
    out = pepper_reschedule(
        item_id=9999,
        new_start="2026-06-09T10:00:00+00:00",
        new_end="2026-06-09T10:30:00+00:00",
        day="2026-06-09",
    )
    assert out["success"] is False


def test_set_deadline_tool_rejects_unknown_item(conn):
    out = pepper_set_deadline(
        item_id=99999,
        deadline="2026-06-12T17:00:00+00:00",
        effort_minutes=360,
    )
    assert out["success"] is False
    assert out["data"] is None
    assert out["error"] is not None


def test_onboard_returns_err_when_memory_unwired(conn):
    from pepper.integration import hermes
    hermes.reset()
    out = pepper_onboard()
    assert out["success"] is False
    assert out["error"] is not None


def test_pepper_cancel_item_cancels(conn):
    from pepper.services import schedule_service
    item = schedule_service.add_event(
        conn, title="Dropme", start_time="2026-06-09T09:00:00+00:00",
        end_time="2026-06-09T10:00:00+00:00",
    )
    res = pepper_cancel_item(item.id)
    assert res["success"] is True
    assert res["data"]["status"] == "cancelled"

    err = pepper_cancel_item(999999)
    assert err["success"] is False
    assert "not found" in err["error"]


def test_resolve_conflict_surfaces_conflicts_payload(conn):
    from pepper.services import priority_service, schedule_service
    for i in range(3):
        it = schedule_service.add_event(
            conn, title=f"a{i}", start_time="2026-06-09T09:00:00+00:00",
            end_time="2026-06-09T10:00:00+00:00", commitment="promise_to_others",
            stakes="one_shot",
        )
        priority_service.recompute_scores(conn, it.id)

    res = pepper_resolve_conflict(day="2026-06-09")
    assert res["success"] is True
    assert res["data"]["action"] == "impossible"
    assert res["data"]["conflicts"]          # conflict report surfaced
    assert "options" in res["data"]          # key always present (empty here)
