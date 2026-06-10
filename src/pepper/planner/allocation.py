from __future__ import annotations

import sqlite3
from datetime import timedelta

from pepper.planner.slots import Slot, free_slots
from pepper.repositories import goal_repo, item_repo
from pepper.time_util import parse_iso, to_iso

HORIZON_DAYS = 14


def allocate_sessions(
    conn: sqlite3.Connection, item_id: int, *, from_day: str, session_minutes: int = 90,
    day_start_min: int = 540, day_end_min: int = 1080,
) -> list[Slot]:
    item = item_repo.get_item(conn, item_id)
    if item is None or not item.effort_estimate or not item.deadline:
        return []
    goal = goal_repo.get_for_item(conn, item_id)
    remaining = item.effort_estimate
    reserved: list[Slot] = []
    day = parse_iso(f"{from_day}T00:00:00+00:00")
    deadline = parse_iso(item.deadline)
    while remaining > 0 and day < deadline and (day - parse_iso(f"{from_day}T00:00:00+00:00")).days < HORIZON_DAYS:
        day_str = day.date().isoformat()
        for slot in free_slots(conn, day_str, day_start_min=day_start_min,
                               day_end_min=day_end_min, min_minutes=15):
            if remaining <= 0:
                break
            cursor = parse_iso(slot.start)
            slot_end = parse_iso(slot.end)
            while remaining > 0:
                space = int((slot_end - cursor).total_seconds() // 60)
                take = min(session_minutes, space, remaining)
                # stop filling this slot once only a tiny scrap remains,
                # unless that scrap still covers the rest of the effort.
                if take < 15 and take < remaining:
                    break
                start = to_iso(cursor)
                cursor += timedelta(minutes=take)
                end = to_iso(cursor)
                item_repo.add_reserved_session(
                    conn, parent_item_id=item_id, title=f"Work: {item.title}",
                    start_time=start, end_time=end, goal_id=goal.id if goal else None,
                )
                reserved.append(Slot(start, end, take))
                remaining -= take
        day += timedelta(days=1)
    return reserved
