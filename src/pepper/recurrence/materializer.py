from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta, timezone

from pepper.recurrence.expand import expand
from pepper.repositories import item_repo, recurrence_repo
from pepper.time_util import parse_iso, to_iso

HORIZON_DAYS = 60


def _combine(d: date, hhmm: str, duration: int) -> tuple[str, str]:
    h, m = (int(x) for x in hhmm.split(":"))
    start = datetime.combine(d, time(h, m), tzinfo=timezone.utc)
    return to_iso(start), to_iso(start + timedelta(minutes=duration))


def materialize(conn: sqlite3.Connection, recurrence_id: int, *, horizon_days: int = HORIZON_DAYS,
                today_iso: str | None = None) -> list[int]:
    tmpl = recurrence_repo.get(conn, recurrence_id)
    if tmpl is None:
        return []
    today = parse_iso(today_iso).date() if today_iso else datetime.now(timezone.utc).date()
    start = today
    if tmpl.materialized_through:
        watermark = parse_iso(tmpl.materialized_through).date()
        start = max(start, watermark + timedelta(days=1))
    until = parse_iso(tmpl.until).date() if tmpl.until else None
    created: list[int] = []
    last: date | None = None
    for d in expand(tmpl.freq, tmpl.interval, tmpl.byday, start, horizon_days, until):
        start_iso, end_iso = _combine(d, tmpl.at_time, tmpl.duration_estimate)
        item_id = item_repo.add_series_instance(
            conn, series_id=recurrence_id, type_id=tmpl.type_id, title=tmpl.title,
            start_time=start_iso, end_time=end_iso, location=tmpl.location,
            commitment=tmpl.commitment, counterparty_id=tmpl.counterparty_id,
            temporal_class=tmpl.temporal_class, stakes=tmpl.stakes,
            divisibility=tmpl.divisibility, duration_estimate=tmpl.duration_estimate,
        )
        created.append(item_id)
        last = d
    if last is not None:
        recurrence_repo.set_materialized_through(conn, recurrence_id, to_iso(
            datetime.combine(last, time(0, 0), tzinfo=timezone.utc)))
    return created


def edit_one(conn: sqlite3.Connection, item_id: int) -> None:
    """Edit/cascade of a single instance: detach so regeneration never overwrites it."""
    item_repo.set_detached(conn, item_id)


def edit_all(conn: sqlite3.Connection, recurrence_id: int, *, changes: dict,
             today_iso: str | None = None, horizon_days: int = HORIZON_DAYS) -> list[int]:
    """Update the template and regenerate only the un-materialized, non-detached future tail.
    Past and detached instances are untouched."""
    recurrence_repo.update_fields(conn, recurrence_id, **changes)
    today = today_iso or datetime.now(timezone.utc).date().isoformat()
    today_date = parse_iso(f"{today}T00:00:00+00:00").date()
    tomorrow = to_iso(datetime.combine(today_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc))
    today_midnight = to_iso(datetime.combine(today_date, time(0, 0), tzinfo=timezone.utc))
    item_repo.delete_future_series(conn, recurrence_id, tomorrow)   # delete tomorrow+ (today preserved)
    recurrence_repo.set_materialized_through(conn, recurrence_id, today_midnight)  # -> materialize starts tomorrow
    return materialize(conn, recurrence_id, horizon_days=horizon_days, today_iso=today)
