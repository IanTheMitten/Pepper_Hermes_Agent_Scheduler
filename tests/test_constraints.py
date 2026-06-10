from pepper.cascade.block import Block
from pepper.cascade.constraints import feasible


def ZERO_TRAVEL(a, b):  # noqa: N802
    return 0


def _b(id, start, end, loc=None, **kw):
    return Block(id=id, start=start, end=end, min_duration=kw.get("min", end - start),
                 rigidity=kw.get("r", 0.5), protection=kw.get("p", 0.5), location=loc,
                 divisible=kw.get("div", False), earliest=kw.get("e", 0),
                 latest=kw.get("l", 1440), anchor=kw.get("anchor", False))


def test_non_overlapping_is_feasible():
    assert feasible([_b(1, 540, 570), _b(2, 600, 660)], ZERO_TRAVEL) is True


def test_overlap_is_infeasible():
    assert feasible([_b(1, 540, 600), _b(2, 570, 630)], ZERO_TRAVEL) is False


def test_travel_gap_required_between_located_blocks():
    blocks = [_b(1, 540, 570, loc="Office"), _b(2, 575, 605, loc="Gym")]

    def travel(a, b):
        return 10 if {a, b} == {"Office", "Gym"} else 0

    assert feasible(blocks, travel) is False  # only 5 min gap, need 10


def test_window_violation_is_infeasible():
    assert feasible([_b(1, 540, 600, l=560)], ZERO_TRAVEL) is False
