from pepper.learning.seeds import seed_estimate


def test_known_seed_returns_duration_and_factors():
    seed = seed_estimate("standup")
    assert seed is not None
    assert seed["duration"] == 30
    assert seed["divisibility"] == "atomic"


def test_unknown_seed_is_none():
    assert seed_estimate("underwater basket weaving") is None
