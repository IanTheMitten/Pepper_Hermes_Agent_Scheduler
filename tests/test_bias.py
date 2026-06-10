from pepper.learning import bias
from pepper.repositories import type_stats_repo, vector_repo


def test_update_bias_moves_toward_ratio_bounded(conn):
    bias.update_bias(conn, "character", "divisible", ratio=1.6)
    f1 = bias.get_bias(conn, "character", "divisible")
    assert 1.0 < f1 < 1.6  # damped toward 1.6, not all the way
    for _ in range(40):
        bias.update_bias(conn, "character", "divisible", ratio=5.0)
    assert bias.get_bias(conn, "character", "divisible") <= 2.0  # clamped


def test_back_off_uses_confident_type_stats_first(conn):
    t = vector_repo.create_type(conn, "standup")
    type_stats_repo.upsert(conn, t, avg_actual=47.0, confidence=0.9, sample_count=12)
    est = bias.estimate_minutes(conn, type_id=t, type_name="standup", factors={}, fallback=60)
    assert est == 47


def test_back_off_falls_back_to_seed_times_personal_bias(conn):
    t = vector_repo.create_type(conn, "deep_work")  # no type_stats yet
    bias.update_bias(conn, "character", "divisible", ratio=1.5)
    bias.update_bias(conn, "character", "divisible", ratio=1.5)
    est = bias.estimate_minutes(
        conn, type_id=t, type_name="deep_work",
        factors={"divisibility": "divisible"}, fallback=60,
    )
    assert est > 90  # seed 90 padded up by the open-ended-work bias
