from __future__ import annotations

from datetime import datetime, timezone


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 string; naive values are treated as UTC."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def duration_minutes(start: str, end: str) -> int:
    delta = parse_iso(end) - parse_iso(start)
    return int(delta.total_seconds() // 60)


def overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    return parse_iso(a_start) < parse_iso(b_end) and parse_iso(b_start) < parse_iso(a_end)
