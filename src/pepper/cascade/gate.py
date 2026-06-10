from __future__ import annotations

from dataclasses import dataclass

from pepper.cascade.engine import Solution

GATE_MARGIN = 2.0  # cost lead for "obvious"; tune-later, tightens as prefs mature (M7)


@dataclass(frozen=True)
class GateDecision:
    action: str                  # "apply" | "escalate" | "impossible"
    chosen: Solution | None
    options: list[Solution]


def decide(solutions: list[Solution], margin: float = GATE_MARGIN) -> GateDecision:
    if not solutions:
        return GateDecision("impossible", None, [])
    if len(solutions) == 1:
        return GateDecision("apply", solutions[0], solutions)
    best, second = solutions[0], solutions[1]
    if second.cost - best.cost >= margin:
        return GateDecision("apply", best, solutions)
    return GateDecision("escalate", None, solutions)
