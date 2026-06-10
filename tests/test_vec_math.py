import math

from pepper.ml.vec_math import cosine, weighted_centroid


def test_cosine_identical_is_one():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_orthogonal_is_zero():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_handles_zero_vector():
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_weighted_centroid_pulls_toward_heavier_weight():
    c = weighted_centroid([[0.0, 0.0], [2.0, 0.0]], [1.0, 3.0])
    assert math.isclose(c[0], 1.5)
    assert math.isclose(c[1], 0.0)
