from pepper.repositories import person_repo


def test_create_and_get(conn):
    pid = person_repo.create(conn, "Sam", relationship="partner",
                             counterparty_weight="high", weight_source="user_set")
    p = person_repo.get(conn, pid)
    assert p.display_name == "Sam"
    assert p.counterparty_weight == "high"


def test_aliases_resolve_to_one_identity(conn):
    pid = person_repo.create(conn, "Mark")
    person_repo.add_alias(conn, pid, "Mark the designer")
    assert person_repo.find_by_name(conn, "Mark") == [pid]
    assert person_repo.find_by_name(conn, "Mark the designer") == [pid]


def test_add_alias_is_idempotent(conn):
    pid = person_repo.create(conn, "Mark")
    person_repo.add_alias(conn, pid, "Mark the designer")
    person_repo.add_alias(conn, pid, "Mark the designer")  # duplicate -> no-op
    assert person_repo.find_by_name(conn, "Mark the designer") == [pid]
    rows = conn.execute(
        "SELECT COUNT(*) AS c FROM person_aliases WHERE person_id = ? AND alias = ?",
        (pid, "Mark the designer"),
    ).fetchone()
    assert rows["c"] == 1


def test_context_fingerprints_accumulate(conn):
    pid = person_repo.create(conn, "Mark")
    person_repo.add_context(conn, pid, "activity", "lunch")
    person_repo.add_context(conn, pid, "activity", "lunch")
    ctx = person_repo.get_context(conn, pid)
    assert ("activity", "lunch", 2) in [(c.signal_type, c.signal_value, c.count) for c in ctx]
