from pepper.cascade.engine import Solution
from pepper.cascade.gate import decide


def _sol(cost):
    return Solution(placed=[], anchors=[], dropped=[], deferred={}, cost=cost, levers={})


def test_single_option_applies_silently():
    d = decide([_sol(10.0)], margin=5.0)
    assert d.action == "apply"
    assert d.chosen.cost == 10.0


def test_dominant_winner_applies_silently():
    d = decide([_sol(10.0), _sol(20.0)], margin=5.0)
    assert d.action == "apply"


def test_close_options_escalate():
    d = decide([_sol(10.0), _sol(11.0)], margin=5.0)
    assert d.action == "escalate"
    assert len(d.options) == 2


def test_no_options_is_impossible():
    d = decide([], margin=5.0)
    assert d.action == "impossible"
