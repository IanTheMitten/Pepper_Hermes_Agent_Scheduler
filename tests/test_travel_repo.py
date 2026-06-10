from pepper.repositories import travel_repo


def test_get_returns_default_for_unknown_pair(conn):
    assert travel_repo.get(conn, "Home", "Office", default=25) == 25


def test_put_then_get_uses_learned_value(conn):
    travel_repo.put(conn, "Home", "Office", 22, source="learned")
    assert travel_repo.get(conn, "Home", "Office", default=25) == 22
    # symmetric lookup
    assert travel_repo.get(conn, "Office", "Home", default=25) == 22


def test_same_location_is_zero(conn):
    assert travel_repo.get(conn, "Office", "Office", default=25) == 0
