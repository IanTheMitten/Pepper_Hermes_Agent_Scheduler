from __future__ import annotations

# Ordering is fixed by the lever hierarchy; magnitudes are tune-later constants.
LEVER_PENALTY = {
    "absorb": 1.0,
    "compress": 2.0,
    "shift": 3.0,
    "split": 4.0,
    "reorder": 5.0,
    "drop": 6.0,
}
COMPRESSION_PENALTY_PER_MIN = 0.05
DROP_SURCHARGE = 5.0


def move_cost(protection: float, lever: str) -> float:
    return protection * LEVER_PENALTY[lever]


def compress_cost(protection: float, minutes_cut: int) -> float:
    return move_cost(protection, "compress") + COMPRESSION_PENALTY_PER_MIN * minutes_cut


def drop_cost(protection: float) -> float:
    return move_cost(protection, "drop") + DROP_SURCHARGE
