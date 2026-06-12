from __future__ import annotations

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from pepper.db.connection import get_connection
from pepper.db.migrations import migrate
from pepper.integration import hermes
from pepper.mcp.schemas import AddEventInput, AddTaskInput, GetScheduleInput
from pepper.ml.embedder import get_embed_fn
from pepper.persons.resolution import resolve
from pepper.recurrence.materializer import materialize
from pepper.repositories import item_repo, objective_repo, person_repo, project_repo, recurrence_repo, rule_repo
from pepper.repositories.item_repo import get_item as item_repo_get
from pepper.services import briefing_service, cascade_service, classification_service, learning_service, onboarding_service, planner_service, priority_service, schedule_service, suggestion_service

mcp = FastMCP("pepper")


def bootstrap() -> None:
    """Ensure the database schema exists before the server handles any tool call.

    Each tool opens its own connection to the shared DB file, so migrating once
    at process startup is enough for the schema to persist across those calls.
    """
    conn = get_connection()
    try:
        migrate(conn)
    finally:
        conn.close()


def _ok(data) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


@mcp.tool()
def pepper_add_event(
    title: str,
    start_time: str,
    end_time: str,
    location: str | None = None,
    commitment: str = "solo",
    counterparty_id: int | None = None,
    stakes: str = "reschedulable",
) -> dict:
    """Add a fixed-time event (meeting, appointment). Times are ISO-8601."""
    try:
        data = AddEventInput(
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            commitment=commitment,
            counterparty_id=counterparty_id,
            stakes=stakes,
        )
    except ValidationError as exc:
        return _err(str(exc))
    conn = get_connection()
    try:
        item = schedule_service.add_event(conn, **data.model_dump())
        classification_service.classify_and_assign(conn, item.id, item.title, get_embed_fn())
        priority_service.recompute_with_context(conn, item.id, day=item.start_time[:10]
                                                if item.start_time else "1970-01-01")
        return _ok(asdict(item_repo_get(conn, item.id)))
    finally:
        conn.close()


@mcp.tool()
def pepper_add_task(
    title: str,
    duration_estimate: int,
    deadline: str | None = None,
    divisibility: str = "atomic",
    stakes: str = "reschedulable",
) -> dict:
    """Capture a deadline-driven or flexible task. Unscheduled until placed."""
    try:
        data = AddTaskInput(
            title=title,
            duration_estimate=duration_estimate,
            deadline=deadline,
            divisibility=divisibility,
            stakes=stakes,
        )
    except ValidationError as exc:
        return _err(str(exc))
    conn = get_connection()
    try:
        item = schedule_service.add_task(conn, **data.model_dump())
        classification_service.classify_and_assign(conn, item.id, item.title, get_embed_fn())
        priority_service.recompute_with_context(conn, item.id, day=item.start_time[:10]
                                                if item.start_time else "1970-01-01")
        return _ok(asdict(item_repo_get(conn, item.id)))
    finally:
        conn.close()


@mcp.tool()
def pepper_get_schedule(start_time: str, end_time: str) -> dict:
    """Return scheduled items overlapping the given ISO-8601 time range."""
    try:
        data = GetScheduleInput(start_time=start_time, end_time=end_time)
    except ValidationError as exc:
        return _err(str(exc))
    conn = get_connection()
    try:
        items = schedule_service.get_schedule(conn, **data.model_dump())
        return _ok(items)
    finally:
        conn.close()


@mcp.tool()
def pepper_set_item_type(item_id: int, type_name: str, title: str) -> dict:
    """Confirm or correct an item's activity type; teaches the classifier."""
    if not type_name.strip():
        return _err("type_name must be non-empty")
    conn = get_connection()
    try:
        type_id = classification_service.set_item_type(
            conn, item_id, type_name, title, get_embed_fn()
        )
        return _ok({"item_id": item_id, "type_id": type_id})
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_mark_progress(
    item_id: int, actual_minutes: int, outcome: str = "done", scope_reached: float | None = None
) -> dict:
    """Record completion or partial progress; appends a Layer-1 observation and re-learns."""
    if outcome not in ("done", "partial", "dropped_pressure", "dropped_user"):
        return _err(f"invalid outcome: {outcome}")
    if actual_minutes <= 0:
        return _err("actual_minutes must be positive")
    conn = get_connection()
    try:
        learning_service.record_completion(
            conn, item_id, actual_minutes=actual_minutes, outcome=outcome,
            scope_reached=scope_reached,
        )
        return _ok({"item_id": item_id, "outcome": outcome})
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_cancel_item(item_id: int) -> dict:
    """Cancel an item (status 'cancelled'); a deliberate drop, no learning logged."""
    conn = get_connection()
    try:
        cascade_service.cancel_item(conn, item_id)
        return _ok(asdict(item_repo_get(conn, item_id)))
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_resolve_person(
    name: str,
    relationship: str | None = None,
    counterparty_weight: str | None = None,
    activity: str | None = None,
    location: str | None = None,
) -> dict:
    """Resolve a referenced person to a stable id; create or disambiguate as needed."""
    context = {k: v for k, v in {"activity": activity, "location": location}.items() if v}
    conn = get_connection()
    try:
        result = resolve(conn, name, context)
        if result.status == "found":
            if counterparty_weight:
                person_repo.set_weight(conn, result.person_id, counterparty_weight, "user_set")
            return _ok({"status": "found", "person_id": result.person_id})
        if result.status == "ambiguous":
            return _ok({"status": "ambiguous", "candidates": result.candidates})
        person_id = person_repo.create(
            conn, name, relationship=relationship,
            counterparty_weight=counterparty_weight or "none",
            weight_source="user_set" if counterparty_weight else "inferred",
        )
        for stype, sval in context.items():
            person_repo.add_context(conn, person_id, stype, sval)
        return _ok({"status": "created", "person_id": person_id})
    finally:
        conn.close()


@mcp.tool()
def pepper_set_priority_factors(
    item_id: int,
    commitment: str | None = None,
    temporal_class: str | None = None,
    stakes: str | None = None,
    divisibility: str | None = None,
    counterparty_id: int | None = None,
) -> dict:
    """Override an item's organic priority factors and recompute its R/P scores."""
    factors = {k: v for k, v in {
        "commitment": commitment, "temporal_class": temporal_class, "stakes": stakes,
        "divisibility": divisibility, "counterparty_id": counterparty_id,
    }.items() if v is not None}
    conn = get_connection()
    try:
        item_repo.set_factors(conn, item_id, **factors)
        item = item_repo_get(conn, item_id)
        priority_service.recompute_with_context(
            conn, item_id,
            day=item.start_time[:10] if item and item.start_time else "1970-01-01")
        return _ok(asdict(item_repo_get(conn, item_id)))
    finally:
        conn.close()


@mcp.tool()
def pepper_reschedule(item_id: int, new_start: str, new_end: str, day: str) -> dict:
    """Move an item to a new time, then re-flow the day around the pin."""
    conn = get_connection()
    try:
        result = cascade_service.reschedule(conn, item_id, new_start, new_end, day)
        return _ok({"action": result.action, "moved": result.moved,
                    "options": result.options, "conflicts": result.conflicts})
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_delay_item(item_id: int, minutes: int, day: str) -> dict:
    """Push an item forward by N minutes and cascade the impact."""
    conn = get_connection()
    try:
        result = cascade_service.delay_item(conn, item_id, minutes, day)
        return _ok({"action": result.action, "moved": result.moved,
                    "options": result.options, "conflicts": result.conflicts})
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_resolve_conflict(day: str) -> dict:
    """Re-flow a day to resolve any overlaps; returns the chosen resolution."""
    conn = get_connection()
    try:
        result = cascade_service.reflow(conn, day)
        return _ok({"action": result.action, "moved": result.moved,
                    "options": result.options, "conflicts": result.conflicts})
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_set_deadline(item_id: int, deadline: str, effort_minutes: int,
                        total_scope: float | None = None) -> dict:
    """Set a task's deadline + total effort; creates a goal and recomputes rigidity."""
    conn = get_connection()
    try:
        planner_service.set_deadline(conn, item_id, deadline=deadline,
                                     effort_minutes=effort_minutes, total_scope=total_scope)
        return _ok(asdict(item_repo_get(conn, item_id)))
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_add_project(title: str, deadline: str | None = None) -> dict:
    """Create a project grouping tasks under a shared deadline (roll-up + projection)."""
    conn = get_connection()
    try:
        pid = project_repo.create(conn, title, deadline=deadline)
        return _ok({"project_id": pid, "title": title})
    finally:
        conn.close()


@mcp.tool()
def pepper_add_recurrence(title: str, freq: str, at_time: str, duration_estimate: int,
                          byday: str | None = None, interval: int = 1,
                          location: str | None = None, until: str | None = None) -> dict:
    """Declare a recurring series; materializes pre-trusted instances over the horizon."""
    if freq not in {"daily", "weekly", "monthly"}:
        return _err("freq must be one of: daily, weekly, monthly")
    conn = get_connection()
    try:
        rid = recurrence_repo.create(
            conn, title=title, type_id=None, freq=freq, interval=interval, byday=byday,
            at_time=at_time, duration_estimate=duration_estimate, until=until, location=location,
            commitment="solo", counterparty_id=None, temporal_class="fixed_time",
            stakes="reschedulable", divisibility="atomic",
        )
        created = materialize(conn, rid)
        return _ok({"recurrence_id": rid, "instances_created": len(created)})
    finally:
        conn.close()


@mcp.tool()
def pepper_edit_recurrence(recurrence_id: int, scope: str = "all", instance_id: int | None = None,
                           at_time: str | None = None, duration_estimate: int | None = None,
                           location: str | None = None) -> dict:
    """Edit a recurring series: scope='one' detaches an instance, scope='all' regenerates the tail."""
    from pepper.recurrence.materializer import edit_all, edit_one
    if scope not in {"one", "all"}:
        return _err("scope must be 'one' or 'all'")
    conn = get_connection()
    try:
        if scope == "one":
            if instance_id is None:
                return _err("instance_id required for scope='one'")
            edit_one(conn, instance_id)
            return _ok({"detached": instance_id})
        changes = {k: v for k, v in {"at_time": at_time, "duration_estimate": duration_estimate,
                                     "location": location}.items() if v is not None}
        created = edit_all(conn, recurrence_id, changes=changes)
        return _ok({"regenerated": len(created)})
    finally:
        conn.close()


@mcp.tool()
def pepper_add_rule(kind: str, param: str, target_type_id: int | None = None) -> dict:
    """Declare a standing rule (kind='no_before' 'HH:MM', or 'cost_bias' factor)."""
    if kind not in ("no_before", "cost_bias"):
        return _err(f"unsupported rule kind: {kind}")
    conn = get_connection()
    try:
        rid = rule_repo.add(conn, kind=kind, target_type_id=target_type_id, param=param)
        return _ok({"rule_id": rid})
    finally:
        conn.close()


@mcp.tool()
def pepper_set_objective(description: str, target_type_id: int | None = None,
                         weight: float = 1.1, until: str | None = None) -> dict:
    """Declare a time-scoped north-star objective (a bounded global soft bias)."""
    conn = get_connection()
    try:
        oid = objective_repo.create(conn, description, target_type_id=target_type_id,
                                    weight=weight, until=until)
        return _ok({"objective_id": oid})
    finally:
        conn.close()


@mcp.tool()
def pepper_suggest_slot(item_id: int, day: str) -> dict:
    """Suggest where to place an item on a day (YYYY-MM-DD): ranks free slots by the
    user's learned time-of-day habit for the item's type, using the learned duration
    estimate. Read-only — enact a chosen option via pepper_reschedule."""
    conn = get_connection()
    try:
        return _ok(suggestion_service.suggest_slots(conn, item_id, day))
    except ValueError as exc:
        return _err(str(exc))
    finally:
        conn.close()


@mcp.tool()
def pepper_briefing(day: str) -> dict:
    """Proactive day briefing (day is YYYY-MM-DD): the schedule plus surfaced risks —
    overlapping items, deadline tasks projected at risk, items whose booked duration
    diverges from the learned actual, and looming unscheduled deadline tasks."""
    conn = get_connection()
    try:
        return _ok(briefing_service.build_briefing(conn, day))
    finally:
        conn.close()


@mcp.tool()
def pepper_onboard() -> dict:
    """Run adaptive onboarding: read Hermes memory, seed people, report which topics to ask."""
    conn = get_connection()
    try:
        memory = hermes.get_memory()
        seeded = onboarding_service.seed_persons(conn, memory)
        plan = onboarding_service.build_plan(memory)
        gaps = [t.topic for t in plan if t.status == "ask"]
        return _ok({"persons_seeded": seeded, "ask_topics": gaps})
    except RuntimeError as exc:
        return _err(str(exc))
    finally:
        conn.close()
