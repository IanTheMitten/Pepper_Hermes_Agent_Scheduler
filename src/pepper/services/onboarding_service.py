from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from pepper.integration.hermes import HermesMemory
from pepper.repositories import person_repo

# (topic, memory_key) — the high-leverage, stable, costly-to-learn facts. Reminder
# lead-times are deliberately NOT asked (5/1 defaults apply).
TOPICS: list[tuple[str, str]] = [
    ("daily_rhythm", "day_bounds"),
    ("locations_commute", "locations"),
    ("fixed_commitments", "recurring_anchors"),
    ("top_people", "important_people"),
    ("hard_lines", "hard_rules"),
    ("peak_focus", "focus_hours"),
]


@dataclass(frozen=True)
class TopicSlot:
    topic: str
    status: str          # "prefilled" | "ask"
    value: dict | None


def build_plan(memory: HermesMemory) -> list[TopicSlot]:
    """Adaptive: query Hermes memory first, ask only what's missing."""
    plan: list[TopicSlot] = []
    for topic, key in TOPICS:
        found = memory.query(key)
        plan.append(TopicSlot(topic, "prefilled" if found else "ask", found))
    return plan


def seed_persons(conn: sqlite3.Connection, memory: HermesMemory) -> int:
    """Seed the few top-priority people from Hermes's Honcho user model."""
    people = memory.query("important_people") or []
    created = 0
    for entry in people:
        if person_repo.find_by_name(conn, entry["name"]):
            continue
        person_repo.create(conn, entry["name"], relationship=entry.get("relationship"),
                           counterparty_weight=entry.get("weight", "high"),
                           weight_source="user_set")
        created += 1
    return created
