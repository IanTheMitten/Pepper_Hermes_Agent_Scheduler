from __future__ import annotations

CONFIDENCE_GATE = 8  # samples for "mature" (tune-later)


def alpha(sample_index: int, floor: float = 0.2) -> float:
    """Sample-gated weight for the n-th sample: a running mean early (1/n),
    sliding to a recency-weighted EWMA (floor) once the bucket matures."""
    return max(floor, 1.0 / sample_index)


def ewma_update(prev_mean: float, x: float, a: float) -> float:
    return prev_mean + a * (x - prev_mean)


def fold(values: list[float], floor: float = 0.2) -> tuple[float, float, int]:
    """Fold a sequence into (mean, spread, count). Spread is an EWMA of absolute deviation."""
    mean = 0.0
    spread = 0.0
    for n, x in enumerate(values, start=1):
        a = alpha(n, floor)
        if n == 1:
            mean = float(x)
            spread = 0.0
            continue
        dev = abs(x - mean)
        spread = spread + a * (dev - spread)
        mean = ewma_update(mean, float(x), a)
    return mean, spread, len(values)


def confidence(sample_count: int, spread: float, mean: float, gate: int = CONFIDENCE_GATE) -> float:
    """Enough samples AND low spread -> high confidence -> go silent."""
    if sample_count == 0:
        return 0.0
    samples_factor = min(1.0, sample_count / gate)
    rel_spread = spread / mean if mean > 0 else spread
    spread_factor = 1.0 / (1.0 + rel_spread)
    return samples_factor * spread_factor
