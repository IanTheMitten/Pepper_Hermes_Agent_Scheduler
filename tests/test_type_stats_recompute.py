from pepper.repositories import observation_repo, type_stats_repo, vector_repo
from pepper.services import learning_service


def test_recompute_learns_average_duration(conn):
    t = vector_repo.create_type(conn, "standup")
    for actual in (46, 44, 48, 45):
        observation_repo.append(
            conn, type_id=t, item_id=None, estimated=30, actual=actual,
            scheduled_start="2026-06-07T09:00:00+00:00", outcome="done",
        )
    learning_service.recompute(conn, t)
    stats = type_stats_repo.get(conn, t)
    assert 43 <= stats.avg_actual <= 49
    assert stats.overrun > 0  # actuals exceed the 30-min estimate
    assert stats.sample_count == 4


def test_recompute_tracks_drop_tendency(conn):
    t = vector_repo.create_type(conn, "gym")
    observation_repo.append(conn, type_id=t, item_id=None, estimated=60, actual=0,
                            outcome="dropped_pressure")
    observation_repo.append(conn, type_id=t, item_id=None, estimated=60, actual=60,
                            outcome="done")
    learning_service.recompute(conn, t)
    assert type_stats_repo.get(conn, t).drop_tendency == 0.5
