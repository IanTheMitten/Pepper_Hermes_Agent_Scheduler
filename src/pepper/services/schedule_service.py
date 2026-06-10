from __future__ import annotations

import sqlite3
from dataclasses import asdict

from pepper.domain.item import Item
from pepper.repositories import item_repo
from pepper.time_util import duration_minutes


def add_event(
    conn: sqlite3.Connection,
    *,
    title: str,
    start_time: str,
    end_time: str,
    location: str | None = None,
    commitment: str = "solo",
    counterparty_id: int | None = None,
    stakes: str = "reschedulable",
    type_id: int | None = None,
) -> Item:
    duration = duration_minutes(start_time, end_time)
    if duration <= 0:
        raise ValueError("end_time must be after start_time")
    item_id = item_repo.add_item(
        conn,
        title=title,
        start_time=start_time,
        end_time=end_time,
        duration_estimate=duration,
        min_duration=duration,
        location=location,
        type_id=type_id,
        commitment=commitment,
        counterparty_id=counterparty_id,
        temporal_class="fixed_time",
        stakes=stakes,
        divisibility="atomic",
    )
    return item_repo.get_item(conn, item_id)


def add_task(
    conn: sqlite3.Connection,
    *,
    title: str,
    duration_estimate: int,
    deadline: str | None = None,
    divisibility: str = "atomic",
    stakes: str = "reschedulable",
    type_id: int | None = None,
) -> Item:
    if duration_estimate <= 0:
        raise ValueError("duration_estimate must be positive")
    item_id = item_repo.add_item(
        conn,
        title=title,
        start_time=None,
        end_time=None,
        duration_estimate=duration_estimate,
        min_duration=duration_estimate,
        type_id=type_id,
        temporal_class="deadline" if deadline else "anytime",
        deadline=deadline,
        stakes=stakes,
        divisibility=divisibility,
    )
    return item_repo.get_item(conn, item_id)


def get_schedule(
    conn: sqlite3.Connection, *, start_time: str, end_time: str
) -> list[dict]:
    return [asdict(item) for item in item_repo.list_in_range(conn, start_time, end_time)]
