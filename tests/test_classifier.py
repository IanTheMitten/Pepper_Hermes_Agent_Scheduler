from pepper.ml.classifier import classify
from pepper.repositories import vector_repo

FAKE = {
    "standup": [1.0, 0.0, 0.0],
    "daily standup": [0.96, 0.1, 0.0],
    "gym session": [0.0, 1.0, 0.0],
    "buy groceries": [0.0, 0.0, 1.0],
}


def fake_embed(text: str) -> list[float]:
    return FAKE[text]


def _seed(conn):
    standup = vector_repo.create_type(conn, "standup")
    vector_repo.add_vector(conn, standup, FAKE["standup"], confidence=1.0)
    gym = vector_repo.create_type(conn, "gym")
    vector_repo.add_vector(conn, gym, FAKE["gym session"], confidence=1.0)
    return standup, gym


def test_confident_match_assigns(conn):
    standup, _ = _seed(conn)
    result = classify(conn, "daily standup", fake_embed, high=0.85, low=0.55)
    assert result.decision == "assign"
    assert result.type_id == standup
    assert result.score > 0.85


def test_no_match_proposes_new(conn):
    _seed(conn)
    result = classify(conn, "buy groceries", fake_embed, high=0.85, low=0.55)
    assert result.decision == "new"
    assert result.type_id is None


def test_no_types_yet_is_new(conn):
    result = classify(conn, "standup", fake_embed)
    assert result.decision == "new"


def test_between_thresholds_is_uncertain(conn):
    standup, _ = _seed(conn)

    def embed(_text):
        return [0.7, 0.7, 0.0]  # cosine ~0.707 to the [1,0,0] standup centroid

    result = classify(conn, "ambiguous thing", embed, high=0.85, low=0.55)
    assert result.decision == "uncertain"
    assert result.type_id == standup
    assert 0.55 <= result.score < 0.85
