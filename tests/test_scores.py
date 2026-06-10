from pepper.priority.scores import (
    base_protection,
    dynamic_rigidity,
    effective_protection,
    slack_ratio,
)


def test_anniversary_gets_max_protection():
    p = base_protection(commitment="promise_to_others", counterparty_weight="high",
                        stakes="one_shot")
    assert p == 1.0


def test_solo_repeatable_is_low_protection():
    assert base_protection(commitment="solo", counterparty_weight="none",
                          stakes="trivial_repeatable") == 0.0


def test_dynamic_rigidity_is_convex_and_caps_at_one():
    base = 0.4
    far = dynamic_rigidity(base, slack_ratio=4.0)
    near = dynamic_rigidity(base, slack_ratio=1.2)
    atrisk = dynamic_rigidity(base, slack_ratio=0.8)
    assert far < near < 1.0
    assert atrisk == 1.0
    # convex: the jump from 2.0->1.2 exceeds the jump from 4.0->2.0
    assert (near - dynamic_rigidity(base, 2.0)) > (dynamic_rigidity(base, 2.0) - far)


def test_effective_protection_modifiers_are_bounded():
    assert effective_protection(0.5, [10.0]) == 0.5 * 1.25  # clamped up
    assert effective_protection(0.5, [0.0]) == 0.5 * 0.8    # clamped down


def test_effective_protection_aggregate_is_bounded():
    # several in-range modifiers must not compound past the bound (nudge, never overturn)
    assert effective_protection(0.5, [1.25, 1.25, 1.25]) == 0.5 * 1.25
    assert effective_protection(0.5, [0.8, 0.8, 0.8]) == 0.5 * 0.8
    # a lone in-range modifier is still applied as-is (clamp is a no-op)
    assert effective_protection(0.5, [1.25]) == 0.625


def test_slack_ratio_handles_zero_effort():
    assert slack_ratio(open_minutes=120, remaining_effort=0) > 100
