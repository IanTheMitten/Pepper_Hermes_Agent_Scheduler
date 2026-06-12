from __future__ import annotations

import sqlite3
from array import array
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TypeRow:
    id: int
    name: str


@dataclass(frozen=True)
class VectorRow:
    id: int
    type_id: int
    embedding: list[float]
    confidence: float
    last_reinforced_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pack(vec: list[float]) -> bytes:
    return array("f", vec).tobytes()


def _unpack(blob: bytes) -> list[float]:
    a = array("f")
    a.frombytes(blob)
    return list(a)


def create_type(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO types (name, created_at) VALUES (?, ?)", (name, _now())
    )
    conn.commit()
    return int(cur.lastrowid)


def list_types(conn: sqlite3.Connection) -> list[TypeRow]:
    rows = conn.execute("SELECT id, name FROM types ORDER BY id").fetchall()
    return [TypeRow(id=r["id"], name=r["name"]) for r in rows]


def get_type_name(conn: sqlite3.Connection, type_id: int) -> str | None:
    row = conn.execute("SELECT name FROM types WHERE id = ?", (type_id,)).fetchone()
    return row["name"] if row else None


def find_type_by_name(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute("SELECT id FROM types WHERE name = ?", (name,)).fetchone()
    return row["id"] if row else None


def add_vector(
    conn: sqlite3.Connection, type_id: int, embedding: list[float], confidence: float = 0.5
) -> int:
    now = _now()
    cur = conn.execute(
        "INSERT INTO vectors (type_id, embedding, confidence, last_reinforced_at, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (type_id, _pack(embedding), confidence, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_by_type(conn: sqlite3.Connection, type_id: int) -> list[VectorRow]:
    rows = conn.execute(
        "SELECT * FROM vectors WHERE type_id = ?", (type_id,)
    ).fetchall()
    return [_row(r) for r in rows]


def get_vector(conn: sqlite3.Connection, vector_id: int) -> VectorRow | None:
    r = conn.execute("SELECT * FROM vectors WHERE id = ?", (vector_id,)).fetchone()
    return _row(r) if r else None


def set_confidence(conn: sqlite3.Connection, vector_id: int, confidence: float) -> None:
    conn.execute(
        "UPDATE vectors SET confidence = ?, last_reinforced_at = ? WHERE id = ?",
        (confidence, _now(), vector_id),
    )
    conn.commit()


def move_to_type(conn: sqlite3.Connection, vector_id: int, new_type_id: int) -> None:
    conn.execute("UPDATE vectors SET type_id = ? WHERE id = ?", (new_type_id, vector_id))
    conn.commit()


def prune_below(conn: sqlite3.Connection, floor: float) -> int:
    cur = conn.execute("DELETE FROM vectors WHERE confidence < ?", (floor,))
    conn.commit()
    return cur.rowcount


def _row(r: sqlite3.Row) -> VectorRow:
    return VectorRow(
        id=r["id"],
        type_id=r["type_id"],
        embedding=_unpack(r["embedding"]),
        confidence=r["confidence"],
        last_reinforced_at=r["last_reinforced_at"],
    )
