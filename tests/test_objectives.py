from pepper.objectives import engine
from pepper.repositories import objective_repo


def test_active_objective_modifies_matching_type(conn):
    objective_repo.create(conn, "Protect deep work", target_type_id=7, weight=1.2)
    assert engine.modifiers(conn, type_id=7) == [1.2]
    assert engine.modifiers(conn, type_id=3) == []


def test_global_objective_applies_to_all(conn):
    objective_repo.create(conn, "Ship season", target_type_id=None, weight=1.15)
    assert engine.modifiers(conn, type_id=99) == [1.15]


def test_inactive_objective_ignored(conn):
    oid = objective_repo.create(conn, "Old", target_type_id=None, weight=1.3)
    objective_repo.deactivate(conn, oid)
    assert engine.modifiers(conn, type_id=1) == []
