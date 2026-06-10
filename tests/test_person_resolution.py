from pepper.persons.resolution import resolve
from pepper.repositories import person_repo


def test_no_match_returns_none(conn):
    r = resolve(conn, "Nobody", context={})
    assert r.status == "none"


def test_single_match_is_found(conn):
    pid = person_repo.create(conn, "Sam")
    r = resolve(conn, "Sam", context={})
    assert r.status == "found"
    assert r.person_id == pid


def test_two_matches_disambiguated_by_context(conn):
    designer = person_repo.create(conn, "Mark")
    person_repo.add_context(conn, designer, "activity", "lunch")
    person_repo.add_context(conn, designer, "activity", "lunch")
    finance = person_repo.create(conn, "Mark")
    person_repo.add_alias(conn, finance, "Mark")  # both answer to "Mark"
    person_repo.add_alias(conn, designer, "Mark")
    r = resolve(conn, "Mark", context={"activity": "lunch"})
    assert r.status == "found"
    assert r.person_id == designer


def test_ambiguous_without_context_surfaces_candidates(conn):
    a = person_repo.create(conn, "Mark")
    b = person_repo.create(conn, "Mark")
    r = resolve(conn, "Mark", context={})
    assert r.status == "ambiguous"
    assert set(r.candidates) == {a, b}
