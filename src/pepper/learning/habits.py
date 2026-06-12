from __future__ import annotations

COMPLETED = ("done", "partial")


def tod_bucket(hour: int) -> str:
    """Time-of-day bucket; must stay in lockstep with observation_repo._tod_bucket."""
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def tod_affinity(observations) -> dict[str, float]:
    """Share of completed observations per time-of-day bucket; {} when no signal."""
    counts: dict[str, int] = {}
    for o in observations:
        if o.outcome in COMPLETED and o.time_of_day:
            counts[o.time_of_day] = counts.get(o.time_of_day, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return {}
    return {bucket: n / total for bucket, n in counts.items()}
