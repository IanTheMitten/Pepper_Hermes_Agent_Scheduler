from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from pepper.integration.hermes import HermesCron, HermesGateway
from pepper.reminders.timing import lead_minutes, remind_at
from pepper.repositories import item_repo, reminder_repo, travel_repo, type_stats_repo

DEFAULT_TRAVEL = 20


@dataclass(frozen=True)
class ReminderPlan:
    remind_at: str
    channel: str


def _learned_slip(conn, type_id: int | None) -> float:
    if type_id is None:
        return 0.0
    stats = type_stats_repo.get(conn, type_id)
    return stats.avg_start_slip or 0.0 if stats else 0.0


def plan_for_item(conn: sqlite3.Connection, item, here: str | None) -> list[ReminderPlan]:
    if not item.start_time:
        return []
    located = bool(item.location)
    travel = travel_repo.get(conn, here, item.location, DEFAULT_TRAVEL) if (located and here) else None
    warn_lead = lead_minutes(located=located, travel=travel,
                             learned_slip=_learned_slip(conn, item.type_id), default_lead=5)
    plans = [
        ReminderPlan(remind_at(item.start_time, warn_lead), "telegram"),
        ReminderPlan(remind_at(item.start_time, 1), "app_push"),
    ]
    if item.end_time:
        plans.append(ReminderPlan(item.end_time, "app_push"))  # completion check
    return plans


def schedule_item_reminders(conn: sqlite3.Connection, item_id: int, cron: HermesCron,
                            here: str | None = None) -> list[ReminderPlan]:
    item = item_repo.get_item(conn, item_id)
    if item is None:
        return []
    plans = plan_for_item(conn, item, here)
    for idx, plan in enumerate(plans):
        reminder_repo.add(conn, item_id=item_id, remind_at=plan.remind_at, channel=plan.channel)
        cron.schedule(f"rem-{item_id}-{idx}", plan.remind_at,
                      {"item_id": item_id, "channel": plan.channel})
    return plans


def fire(message: str, gateway: HermesGateway) -> None:
    gateway.send(message)
