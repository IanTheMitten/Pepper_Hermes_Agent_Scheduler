from __future__ import annotations

import sqlite3

from pepper.repositories import vector_repo


def reinforce(conn: sqlite3.Connection, vector_id: int, step: float = 0.1) -> None:
    v = vector_repo.get_vector(conn, vector_id)
    if v is None:
        return
    vector_repo.set_confidence(conn, vector_id, min(1.0, v.confidence + step))


def correct(conn: sqlite3.Connection, vector_id: int, new_type_id: int) -> None:
    """User reassigned the type: move the vector, removing its pull from the old centroid."""
    vector_repo.move_to_type(conn, vector_id, new_type_id)


def decay_and_prune(
    conn: sqlite3.Connection, decay: float = 0.02, floor: float = 0.05
) -> int:
    """Multiplicatively decay every vector's confidence, then prune below the floor."""
    for t in vector_repo.list_types(conn):
        for v in vector_repo.list_by_type(conn, t.id):
            vector_repo.set_confidence(conn, v.id, v.confidence * (1.0 - decay))
    return vector_repo.prune_below(conn, floor)
