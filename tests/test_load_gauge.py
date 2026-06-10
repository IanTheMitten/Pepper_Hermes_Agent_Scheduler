from pepper.load.gauge import acute_load, chronic_load, protection_multiplier, total_load


def test_acute_load_saturates_on_worst_axis():
    # one brutal axis (0.9) should dominate, not be averaged down
    assert acute_load(density=0.9, day_length=0.1, context_switch=0.1) > 0.9


def test_chronic_accumulates_then_decays_with_rest():
    risen = chronic_load(prev=0.2, dropped_recovery=2, rested=False)
    assert risen > 0.2
    decayed = chronic_load(prev=risen, dropped_recovery=0, rested=True)
    assert decayed < risen


def test_multiplier_is_bounded_and_directional():
    high = total_load(acute=0.9, chronic=0.6)
    assert 0.8 <= protection_multiplier(high, is_recovery=True, is_low_stakes=False) <= 1.25
    assert protection_multiplier(high, is_recovery=True, is_low_stakes=False) > 1.0   # protect recovery
    assert protection_multiplier(high, is_recovery=False, is_low_stakes=True) < 1.0   # shed low-stakes
