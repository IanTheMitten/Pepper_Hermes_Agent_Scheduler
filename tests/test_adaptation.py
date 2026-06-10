from pepper.ml import adaptation
from pepper.repositories import vector_repo


def test_reinforce_raises_confidence_capped(conn):
    t = vector_repo.create_type(conn, "standup")
    v = vector_repo.add_vector(conn, t, [1.0, 0.0], confidence=0.5)
    adaptation.reinforce(conn, v, step=0.2)
    assert vector_repo.get_vector(conn, v).confidence == 0.7
    for _ in range(10):
        adaptation.reinforce(conn, v, step=0.2)
    assert vector_repo.get_vector(conn, v).confidence == 1.0


def test_correct_moves_vector_to_new_type(conn):
    wrong = vector_repo.create_type(conn, "deep_work")
    right = vector_repo.create_type(conn, "exec_meeting")
    v = vector_repo.add_vector(conn, wrong, [0.0, 1.0], confidence=0.5)
    adaptation.correct(conn, v, right)
    assert vector_repo.get_vector(conn, v).type_id == right
    assert vector_repo.list_by_type(conn, wrong) == []


def test_decay_and_prune_removes_stale(conn):
    t = vector_repo.create_type(conn, "standup")
    v = vector_repo.add_vector(conn, t, [1.0, 0.0], confidence=0.12)
    adaptation.decay_and_prune(conn, decay=0.1, floor=0.05)  # 0.12 -> 0.108, kept
    assert vector_repo.get_vector(conn, v) is not None
    adaptation.decay_and_prune(conn, decay=0.9, floor=0.05)  # 0.108 -> ~0.011, pruned
    assert vector_repo.get_vector(conn, v) is None
