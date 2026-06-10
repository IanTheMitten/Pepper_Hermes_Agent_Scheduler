from __future__ import annotations

from datetime import timedelta

from pepper.time_util import parse_iso, to_iso


def lead_minutes(*, located: bool, travel: int | None, learned_slip: float = 0.0,
                 default_lead: int = 5, prep: int = 5, override: int | None = None) -> int:
    """Travel-aware 'leave now' for located items; otherwise default + learned slip.
    A per-item override always wins."""
    if override is not None:
        return override
    if located and travel is not None:
        return travel + prep
    return default_lead + max(0, round(learned_slip))


def remind_at(start_iso: str, lead: int) -> str:
    return to_iso(parse_iso(start_iso) - timedelta(minutes=lead))
