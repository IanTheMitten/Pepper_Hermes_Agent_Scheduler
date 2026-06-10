from pepper.repositories import item_repo, observation_repo, type_stats_repo, vector_repo
from pepper.services import learning_service, schedule_service


def test_record_completion_writes_obs_recomputes_stats_and_bias(conn):
    t = vector_repo.create_type(conn, "standup")
    item = schedule_service.add_event(
        conn, title="standup",
        start_time="2026-06-07T09:00:00+00:00", end_time="2026-06-07T09:30:00+00:00",
        commitment="promise_to_others",
    )
    item_repo.set_type(conn, item.id, t)

    learning_service.record_completion(conn, item.id, actual_minutes=46, outcome="done")

    assert len(observation_repo.list_by_type(conn, t)) == 1
    stats = type_stats_repo.get(conn, t)
    assert stats.avg_actual == 46
    assert item_repo.get_item(conn, item.id).status == "done"


def test_partial_records_scope(conn):
    t = vector_repo.create_type(conn, "deep_work")
    item = schedule_service.add_task(conn, title="roadmap", duration_estimate=120,
                                     divisibility="divisible")
    item_repo.set_type(conn, item.id, t)
    learning_service.record_completion(
        conn, item.id, actual_minutes=80, outcome="partial", scope_reached=2.0
    )
    obs = observation_repo.list_by_type(conn, t)[0]
    assert obs.scope_reached == 2.0
    assert obs.outcome == "partial"
