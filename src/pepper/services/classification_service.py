from __future__ import annotations

import sqlite3

from pepper.ml.classifier import Classification, classify
from pepper.ml.embedder import EmbedFn
from pepper.repositories import item_repo, vector_repo


def classify_and_assign(
    conn: sqlite3.Connection, item_id: int, title: str, embed_fn: EmbedFn
) -> Classification:
    """Reflex path: a confident match sets the type + reinforces; otherwise leave the
    item untyped for Hermes confirmation (wired in M7)."""
    result = classify(conn, title, embed_fn)
    if result.decision == "assign" and result.type_id is not None:
        item_repo.set_type(conn, item_id, result.type_id)
        vector_repo.add_vector(conn, result.type_id, embed_fn(title), confidence=0.6)
    return result


def set_item_type(
    conn: sqlite3.Connection, item_id: int, type_name: str, title: str, embed_fn: EmbedFn
) -> int:
    """Confirmation/correction entry point: bind an item to a (possibly new) type and
    teach the vectors so future titles classify silently."""
    if item_repo.get_item(conn, item_id) is None:
        raise ValueError(f"no item with id {item_id}")
    type_id = vector_repo.find_type_by_name(conn, type_name)
    if type_id is None:
        type_id = vector_repo.create_type(conn, type_name)
    item_repo.set_type(conn, item_id, type_id)
    vector_repo.add_vector(conn, type_id, embed_fn(title), confidence=0.7)
    return type_id
