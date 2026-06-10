from pytest import approx as pytest_approx

from pepper.repositories import vector_repo


def test_create_type_and_add_vector_roundtrip(conn):
    type_id = vector_repo.create_type(conn, "standup")
    vec_id = vector_repo.add_vector(conn, type_id, [0.1, 0.2, 0.3], confidence=0.5)
    rows = vector_repo.list_by_type(conn, type_id)
    assert len(rows) == 1
    assert rows[0].id == vec_id
    assert rows[0].embedding == [pytest_approx(0.1), pytest_approx(0.2), pytest_approx(0.3)]


def test_list_all_types(conn):
    vector_repo.create_type(conn, "standup")
    vector_repo.create_type(conn, "gym")
    assert {t.name for t in vector_repo.list_types(conn)} == {"standup", "gym"}


def test_update_confidence_and_prune(conn):
    type_id = vector_repo.create_type(conn, "standup")
    vec_id = vector_repo.add_vector(conn, type_id, [1.0, 0.0], confidence=0.05)
    vector_repo.set_confidence(conn, vec_id, 0.9)
    assert vector_repo.list_by_type(conn, type_id)[0].confidence == 0.9
    vector_repo.prune_below(conn, 0.1)  # nothing pruned (0.9 > 0.1)
    assert len(vector_repo.list_by_type(conn, type_id)) == 1
    low_id = vector_repo.add_vector(conn, type_id, [0.0, 1.0], confidence=0.05)
    removed = vector_repo.prune_below(conn, 0.1)  # removes the 0.05 vector, keeps the 0.9 one
    assert removed == 1
    remaining = vector_repo.list_by_type(conn, type_id)
    assert [v.id for v in remaining] == [vec_id]
    assert vector_repo.get_vector(conn, low_id) is None
