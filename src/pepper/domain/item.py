from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum


class Commitment(str, Enum):
    solo = "solo"
    promise_to_self = "promise_to_self"
    promise_to_others = "promise_to_others"


class TemporalClass(str, Enum):
    fixed_time = "fixed_time"
    deadline = "deadline"
    anytime = "anytime"


class Stakes(str, Enum):
    trivial_repeatable = "trivial_repeatable"
    reschedulable = "reschedulable"
    one_shot = "one_shot"


class Divisibility(str, Enum):
    atomic = "atomic"
    checkpointed = "checkpointed"
    divisible = "divisible"


class ItemStatus(str, Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    done = "done"
    dropped = "dropped"
    cancelled = "cancelled"


@dataclass(frozen=True)
class Item:
    id: int
    title: str
    start_time: str | None
    end_time: str | None
    duration_estimate: int | None
    min_duration: int | None
    location: str | None
    status: str
    type_id: int | None
    commitment: str
    counterparty_id: int | None
    temporal_class: str
    deadline: str | None
    stakes: str
    divisibility: str
    rigidity_score: float | None
    protection_score: float | None
    goal_id: int | None
    effort_estimate: int | None
    project_id: int | None
    auto_reserved: int
    parent_item_id: int | None
    series_id: int | None
    detached: int
    version: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Item":
        return cls(
            id=row["id"],
            title=row["title"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            duration_estimate=row["duration_estimate"],
            min_duration=row["min_duration"],
            location=row["location"],
            status=row["status"],
            type_id=row["type_id"],
            commitment=row["commitment"],
            counterparty_id=row["counterparty_id"],
            temporal_class=row["temporal_class"],
            deadline=row["deadline"],
            stakes=row["stakes"],
            divisibility=row["divisibility"],
            rigidity_score=row["rigidity_score"],
            protection_score=row["protection_score"],
            goal_id=row["goal_id"],
            effort_estimate=row["effort_estimate"],
            project_id=row["project_id"],
            auto_reserved=row["auto_reserved"],
            parent_item_id=row["parent_item_id"],
            series_id=row["series_id"],
            detached=row["detached"],
            version=row["version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
