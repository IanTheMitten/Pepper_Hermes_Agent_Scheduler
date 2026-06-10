from __future__ import annotations

import math


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def weighted_centroid(vectors: list[list[float]], weights: list[float]) -> list[float]:
    if not vectors:
        raise ValueError("cannot take centroid of empty set")
    dim = len(vectors[0])
    total = sum(weights)
    if total == 0.0:
        total = float(len(vectors))
        weights = [1.0] * len(vectors)
    acc = [0.0] * dim
    for vec, w in zip(vectors, weights):
        for i in range(dim):
            acc[i] += vec[i] * w
    return [v / total for v in acc]
