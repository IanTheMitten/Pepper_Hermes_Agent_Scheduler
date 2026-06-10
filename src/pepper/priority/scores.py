from __future__ import annotations

# Discrete base tables (human-auditable, read like priority rules). Tune-later magnitudes.
_RIGIDITY_BASE = {"fixed_time": 0.9, "deadline": 0.4, "anytime": 0.15}
_COMMITMENT_P = {"solo": 0.0, "promise_to_self": 0.3, "promise_to_others": 0.6}
_COUNTERPARTY_P = {"none": 0.0, "low": 0.1, "high": 0.3}
_STAKES_P = {"trivial_repeatable": 0.0, "reschedulable": 0.2, "one_shot": 0.5}

MODIFIER_MIN, MODIFIER_MAX = 0.8, 1.25


def base_rigidity(temporal_class: str) -> float:
    return _RIGIDITY_BASE.get(temporal_class, 0.15)


def base_protection(*, commitment: str, counterparty_weight: str, stakes: str) -> float:
    raw = (
        _COMMITMENT_P.get(commitment, 0.0)
        + _COUNTERPARTY_P.get(counterparty_weight, 0.0)
        + _STAKES_P.get(stakes, 0.0)
    )
    return min(1.0, raw)


def slack_ratio(open_minutes: float, remaining_effort: float) -> float:
    """open_time_before_deadline / remaining_effort; near-infinite when nothing remains."""
    if remaining_effort <= 0:
        return 999.0
    return open_minutes / remaining_effort


def dynamic_rigidity(base_r: float, slack_ratio: float | None) -> float:
    """R rises convexly as slack_ratio -> 1; at/under 1 (won't fit) it anchors at max."""
    if slack_ratio is None:
        return base_r
    if slack_ratio <= 1.0:
        return 1.0
    lift = (1.0 / slack_ratio) ** 2  # convex in 1/ratio
    return base_r + (1.0 - base_r) * lift


def effective_protection(base_p: float, modifiers: list[float]) -> float:
    """base_P x bounded product of soft modifiers (nudge, never overturn)."""
    factor = 1.0
    for m in modifiers:
        factor *= max(MODIFIER_MIN, min(MODIFIER_MAX, m))
    factor = max(MODIFIER_MIN, min(MODIFIER_MAX, factor))
    return base_p * factor


def compute_scores(
    *,
    temporal_class: str,
    commitment: str,
    counterparty_weight: str,
    stakes: str,
    item_slack_ratio: float | None = None,
    modifiers: list[float] | None = None,
) -> tuple[float, float]:
    r = dynamic_rigidity(base_rigidity(temporal_class), item_slack_ratio)
    p = effective_protection(
        base_protection(commitment=commitment, counterparty_weight=counterparty_weight,
                        stakes=stakes),
        modifiers or [],
    )
    return r, p
