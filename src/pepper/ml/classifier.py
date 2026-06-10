from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from pepper.ml.embedder import EmbedFn
from pepper.ml.vec_math import cosine, weighted_centroid
from pepper.repositories import vector_repo

HIGH_THRESHOLD = 0.85  # tune-later
LOW_THRESHOLD = 0.55  # tune-later


@dataclass(frozen=True)
class Classification:
    decision: str  # "assign" | "uncertain" | "new"
    type_id: int | None
    score: float


def _centroid(conn: sqlite3.Connection, type_id: int) -> list[float] | None:
    vectors = vector_repo.list_by_type(conn, type_id)
    if not vectors:
        return None
    return weighted_centroid([v.embedding for v in vectors], [v.confidence for v in vectors])


def classify(
    conn: sqlite3.Connection,
    title: str,
    embed_fn: EmbedFn,
    high: float = HIGH_THRESHOLD,
    low: float = LOW_THRESHOLD,
) -> Classification:
    types = vector_repo.list_types(conn)
    if not types:
        # No buckets learned yet: the result is always "new", so skip embedding
        # the title (which would load the embedding model for no decision value).
        return Classification("new", None, 0.0)
    query = embed_fn(title)
    best_type: int | None = None
    best_score = 0.0
    for t in types:
        centroid = _centroid(conn, t.id)
        if centroid is None:
            continue
        score = cosine(query, centroid)
        if score > best_score:
            best_score = score
            best_type = t.id
    if best_type is not None and best_score >= high:
        return Classification("assign", best_type, best_score)
    if best_type is not None and best_score >= low:
        return Classification("uncertain", best_type, best_score)
    return Classification("new", None, best_score)
