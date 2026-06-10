from __future__ import annotations

from collections.abc import Callable

from pepper.cascade.block import Block

TravelFn = Callable[[str, str], int]


def _ordered(blocks: list[Block]) -> list[Block]:
    return sorted(blocks, key=lambda b: b.start)


def no_overlap(blocks: list[Block]) -> bool:
    seq = _ordered(blocks)
    return all(seq[i].end <= seq[i + 1].start for i in range(len(seq) - 1))


def within_windows(blocks: list[Block]) -> bool:
    return all(b.start >= b.earliest and b.end <= b.latest for b in blocks)


def floors_ok(blocks: list[Block]) -> bool:
    return all(b.duration >= b.min_duration for b in blocks)


def travel_ok(blocks: list[Block], travel: TravelFn) -> bool:
    seq = _ordered(blocks)
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        if a.location and b.location:
            if b.start - a.end < travel(a.location, b.location):
                return False
    return True


def feasible(blocks: list[Block], travel: TravelFn) -> bool:
    return (
        no_overlap(blocks)
        and within_windows(blocks)
        and floors_ok(blocks)
        and travel_ok(blocks, travel)
    )
