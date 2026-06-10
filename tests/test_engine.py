from pepper.cascade.block import Block
from pepper.cascade.engine import solve


def zero(a, b):
    return 0


def _b(id, start, end, **kw):
    return Block(id=id, start=start, end=end, min_duration=kw.get("min", end - start),
                 rigidity=kw.get("r", 0.4), protection=kw.get("p", 0.5),
                 location=kw.get("loc"), divisible=kw.get("div", False),
                 earliest=kw.get("e", 480), latest=kw.get("l", 1260),
                 anchor=kw.get("anchor", False))


def test_buffer_absorbs_small_overrun_no_other_moves():
    # roadmap overran to 615; lunch at 630 has buffer -> still feasible, cheapest = leave it
    blocks = [_b(1, 570, 615, p=0.7), _b(2, 630, 690, p=0.4)]
    sols = solve(blocks, zero)
    assert sols[0].blocks_by_id()[2].start == 630  # lunch untouched


def test_overlap_resolved_by_moving_lower_priority_block():
    blocks = [_b(1, 570, 640, p=0.8), _b(2, 600, 660, p=0.3)]  # overlap
    sols = solve(blocks, zero)
    best = sols[0]
    b = best.blocks_by_id()
    assert best.is_feasible
    assert b[1].start == 570                                  # higher-P block stays put (absorb)
    assert b[2].start != 600                                  # lower-P block moved off the overlap
    assert b[2].end <= b[1].start or b[2].start >= b[1].end   # and no longer overlaps it


def test_infeasible_day_drops_lowest_protection():
    # Dinner is a fixed anchor. Work (high P) holds 900-1080. Gym can't fit before work
    # (its earliest is 1020) nor between work and dinner (only 30 min) -> lowest-P item drops.
    dinner = _b(3, 1110, 1200, p=1.0, anchor=True)
    work = _b(1, 900, 1080, p=0.8)
    gym = _b(2, 1020, 1110, p=0.15, e=1020, l=1110)
    sols = solve([work, gym, dinner], zero)
    best = sols[0]
    assert 2 in best.dropped                      # gym dropped (lowest P), not work or dinner
    assert best.blocks_by_id()[1].start == 900    # high-P work kept in place
    assert best.blocks_by_id()[3].start == 1110   # anchor untouched
