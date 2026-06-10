from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Person:
    id: int
    display_name: str
    relationship: str | None
    counterparty_weight: str
    weight_source: str


@dataclass(frozen=True)
class ContextSignal:
    signal_type: str
    signal_value: str
    count: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(
    conn: sqlite3.Connection,
    display_name: str,
    *,
    relationship: str | None = None,
    counterparty_weight: str = "none",
    weight_source: str = "inferred",
) -> int:
    now = _now()
    cur = conn.execute(
        "INSERT INTO persons (display_name, relationship, counterparty_weight, "
        "weight_source, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        (display_name, relationship, counterparty_weight, weight_source, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, person_id: int) -> Person | None:
    r = conn.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
    if r is None:
        return None
    return Person(
        id=r["id"],
        display_name=r["display_name"],
        relationship=r["relationship"],
        counterparty_weight=r["counterparty_weight"],
        weight_source=r["weight_source"],
    )


def add_alias(conn: sqlite3.Connection, person_id: int, alias: str) -> None:
    conn.execute("INSERT OR IGNORE INTO person_aliases (person_id, alias) VALUES (?, ?)",
                 (person_id, alias))
    conn.commit()


def find_by_name(conn: sqlite3.Connection, name: str) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM persons WHERE display_name = ? "
        "UNION SELECT person_id FROM person_aliases WHERE alias = ?",
        (name, name),
    ).fetchall()
    return [r[0] for r in rows]


def add_context(
    conn: sqlite3.Connection, person_id: int, signal_type: str, signal_value: str
) -> None:
    conn.execute(
        "INSERT INTO person_context (person_id, signal_type, signal_value, count) VALUES (?,?,?,1) "
        "ON CONFLICT(person_id, signal_type, signal_value) DO UPDATE SET count = count + 1",
        (person_id, signal_type, signal_value),
    )
    conn.commit()


def get_context(conn: sqlite3.Connection, person_id: int) -> list[ContextSignal]:
    rows = conn.execute(
        "SELECT signal_type, signal_value, count FROM person_context WHERE person_id = ?",
        (person_id,),
    ).fetchall()
    return [ContextSignal(r["signal_type"], r["signal_value"], r["count"]) for r in rows]


def set_weight(conn: sqlite3.Connection, person_id: int, weight: str, source: str) -> None:
    conn.execute(
        "UPDATE persons SET counterparty_weight = ?, weight_source = ?, updated_at = ? WHERE id = ?",
        (weight, source, _now(), person_id),
    )
    conn.commit()
