from __future__ import annotations

CHRONIC_RISE = 0.15        # per dropped recovery item (tune-later)
CHRONIC_DECAY = 0.3        # fraction shed on a rested day
MOD_MIN, MOD_MAX = 0.8, 1.25


def acute_load(density: float, day_length: float, context_switch: float) -> float:
    """Today's load, combined saturating so the worst axis counts fully (1 - Π(1 - sᵢ))."""
    product = 1.0
    for s in (density, day_length, context_switch):
        product *= (1.0 - max(0.0, min(1.0, s)))
    return 1.0 - product


def chronic_load(prev: float, dropped_recovery: int, rested: bool) -> float:
    """Recovery-debt accumulator: rises on dropped recovery items, decays with rest."""
    value = prev + CHRONIC_RISE * dropped_recovery
    if rested:
        value *= (1.0 - CHRONIC_DECAY)
    return max(0.0, min(1.0, value))


def total_load(acute: float, chronic: float) -> float:
    return 1.0 - (1.0 - max(0.0, min(1.0, acute))) * (1.0 - max(0.0, min(1.0, chronic)))


def protection_multiplier(load: float, *, is_recovery: bool, is_low_stakes: bool) -> float:
    """Map load into the bounded protection multiplier: recovery up, low-stakes down."""
    if is_recovery:
        return min(MOD_MAX, 1.0 + (MOD_MAX - 1.0) * load)
    if is_low_stakes:
        return max(MOD_MIN, 1.0 - (1.0 - MOD_MIN) * load)
    return 1.0
