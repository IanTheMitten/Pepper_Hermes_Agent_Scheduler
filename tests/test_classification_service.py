import pytest

from pepper.repositories import item_repo, vector_repo
from pepper.services import classification_service as cs
from pepper.services import schedule_service

FAKE = {"daily standup": [1.0, 0.0], "standup": [0.99, 0.0], "random errand": [0.0, 1.0]}


def fake_embed(text):
    return FAKE[text]


def fake_embed_const(vec):
    return lambda _text: vec


def test_confident_capture_gets_typed(conn):
    standup = vector_repo.create_type(conn, "standup")
    vector_repo.add_vector(conn, standup, FAKE["standup"], confidence=1.0)
    item = schedule_service.add_event(
        conn,
        title="daily standup",
        start_time="2026-06-07T09:00:00+00:00",
        end_time="2026-06-07T09:30:00+00:00",
    )
    result = cs.classify_and_assign(conn, item.id, "daily standup", fake_embed)
    assert result.decision == "assign"
    assert item_repo.get_item(conn, item.id).type_id == standup


def test_unknown_capture_left_untyped(conn):
    standup = vector_repo.create_type(conn, "standup")
    vector_repo.add_vector(conn, standup, FAKE["standup"], confidence=1.0)
    item = schedule_service.add_task(conn, title="random errand", duration_estimate=30)
    result = cs.classify_and_assign(conn, item.id, "random errand", fake_embed)
    assert result.decision == "new"
    assert item_repo.get_item(conn, item.id).type_id is None


def test_set_item_type_creates_type_and_teaches_vectors(conn):
    item = schedule_service.add_task(conn, title="walk the dog", duration_estimate=20)
    cs.set_item_type(conn, item.id, "dog_walk", "walk the dog", fake_embed_const([0.5, 0.5]))
    type_id = vector_repo.find_type_by_name(conn, "dog_walk")
    assert item_repo.get_item(conn, item.id).type_id == type_id
    assert len(vector_repo.list_by_type(conn, type_id)) == 1


def test_set_item_type_rejects_unknown_item(conn):
    with pytest.raises(ValueError):
        cs.set_item_type(conn, 9999, "ghost", "ghost title", fake_embed_const([0.1, 0.2]))
