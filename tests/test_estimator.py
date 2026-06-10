import math

from pepper.learning.estimator import alpha, confidence, fold


def test_alpha_is_running_mean_early_then_floors():
    assert alpha(1, floor=0.2) == 1.0
    assert alpha(2, floor=0.2) == 0.5
    assert alpha(10, floor=0.2) == 0.2  # 1/10 < floor -> recency-weighted


def test_fold_tracks_mean_and_spread():
    mean, spread, n = fold([30, 30, 30], floor=0.2)
    assert n == 3
    assert math.isclose(mean, 30.0)
    assert spread == 0.0


def test_fold_recent_values_pull_mean_when_mature():
    # long stable run then a jump: mature alpha tracks the change, doesn't ignore it
    mean, _, _ = fold([30] * 9 + [60], floor=0.3)
    assert mean > 30.0


def test_confidence_rises_with_samples_and_falls_with_spread():
    low = confidence(sample_count=1, spread=0.0, mean=30.0)
    high = confidence(sample_count=20, spread=0.0, mean=30.0)
    noisy = confidence(sample_count=20, spread=30.0, mean=30.0)
    assert high > low
    assert high > noisy
