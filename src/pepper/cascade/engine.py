from __future__ import annotations

from dataclasses import dataclass

from pepper.cascade.block import Block, place, place_compressed, split_head
from pepper.cascade.constraints import TravelFn, feasible
from pepper.cascade.cost import compress_cost, drop_cost, move_cost

DROP_THRESHOLD = 0.25   # only low-protection blocks may be dropped (tune-later)
NODE_BUDGET = 5000
EPSILON = 1.0           # solutions within this cost margin of best are "near-optimal"


@dataclass(frozen=True)
class Solution:
    placed: list[Block]
    anchors: list[Block]
    dropped: list[int]
    deferred: dict[int, int]   # block id -> deferred minutes
    cost: float
    levers: dict[int, str]
    is_feasible: bool = True

    def blocks_by_id(self) -> dict[int, Block]:
        return {b.id: b for b in (*self.placed, *self.anchors)}


def _earliest_fit(occupied: list[Block], dur: int, earliest: int, latest: int,
                  loc: str | None, travel: TravelFn) -> int | None:
    """Earliest start >= earliest where [start, start+dur] fits without overlap, respecting
    travel gaps to the temporally-adjacent occupied blocks."""
    seq = sorted(occupied, key=lambda b: b.start)
    t = earliest
    for blk in seq:
        gap_to = travel(loc, blk.location) if (loc and blk.location) else 0
        if t + dur + gap_to <= blk.start:
            return t if t + dur <= latest else None
        gap_from = travel(blk.location, loc) if (blk.location and loc) else 0
        t = max(t, blk.end + gap_from)
    return t if t + dur <= latest else None


def _fits_at(occupied: list[Block], block: Block, start: int, dur: int, travel: TravelFn) -> bool:
    """True if `block` can stay at `start`: within its window, no overlap, travel gaps respected."""
    end = start + dur
    if start < block.earliest or end > block.latest:
        return False
    for blk in occupied:
        if start < blk.end and blk.start < end:  # overlap
            return False
        if block.location and blk.location:
            if blk.start >= end and blk.start - end < travel(block.location, blk.location):
                return False
            if start >= blk.end and start - blk.end < travel(blk.location, block.location):
                return False
    return True


def solve(blocks: list[Block], travel: TravelFn,
          budget: int = NODE_BUDGET, epsilon: float = EPSILON) -> list[Solution]:
    anchors = [b for b in blocks if b.anchor]
    movable = sorted((b for b in blocks if not b.anchor), key=lambda b: (b.earliest, b.start))
    best: list[float] = [float("inf")]
    found: list[Solution] = []
    nodes = [0]

    def record(placed, dropped, deferred, cost, levers):
        full = [*placed, *anchors]
        if not feasible(full, travel):
            return
        if cost < best[0]:
            best[0] = cost
        found.append(Solution(list(placed), list(anchors), list(dropped), dict(deferred),
                              cost, dict(levers)))

    def branch(i, placed, dropped, deferred, cost, levers):
        if nodes[0] > budget:
            return
        nodes[0] += 1
        if cost >= best[0]:
            return
        if i == len(movable):
            record(placed, dropped, deferred, cost, levers)
            return
        blk = movable[i]
        occupied = [*placed, *anchors]
        # 1) keep at original position if still feasible (absorb); else shift to earliest fit.
        #    This localizes the re-flow: unaffected items stay put, only conflicts move.
        if _fits_at(occupied, blk, blk.start, blk.duration, travel):
            branch(i + 1, [*placed, place(blk, blk.start)], dropped, deferred,
                   cost + move_cost(blk.protection, "absorb"), {**levers, blk.id: "absorb"})
        else:
            start = _earliest_fit(occupied, blk.duration, blk.earliest, blk.latest, blk.location, travel)
            if start is not None:
                branch(i + 1, [*placed, place(blk, start)], dropped, deferred,
                       cost + move_cost(blk.protection, "shift"), {**levers, blk.id: "shift"})
        # 2) compress to floor
        if blk.min_duration < blk.duration:
            cstart = _earliest_fit(occupied, blk.min_duration, blk.earliest, blk.latest,
                                   blk.location, travel)
            if cstart is not None:
                cut = blk.duration - blk.min_duration
                branch(i + 1, [*placed, place_compressed(blk, cstart, blk.min_duration)],
                       dropped, deferred, cost + compress_cost(blk.protection, cut),
                       {**levers, blk.id: "compress"})
        # 3) split (divisible): place min now, defer remainder
        if blk.divisible and blk.min_duration < blk.duration:
            sstart = _earliest_fit(occupied, blk.min_duration, blk.earliest, blk.latest,
                                   blk.location, travel)
            if sstart is not None:
                head, deferred_min = split_head(blk, sstart)
                branch(i + 1, [*placed, head], dropped, {**deferred, blk.id: deferred_min},
                       cost + move_cost(blk.protection, "split"), {**levers, blk.id: "split"})
        # 4) drop (only low protection)
        if blk.protection <= DROP_THRESHOLD:
            branch(i + 1, placed, [*dropped, blk.id], deferred,
                   cost + drop_cost(blk.protection), {**levers, blk.id: "drop"})

    branch(0, [], [], {}, 0.0, {})
    found.sort(key=lambda s: s.cost)
    if not found:
        return []
    cutoff = found[0].cost + epsilon
    return [s for s in found if s.cost <= cutoff]
