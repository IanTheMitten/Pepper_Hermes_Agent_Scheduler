from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from enum import Enum

from pepper.domain.item import Item
from pepper.time_util import parse_iso


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: str | Enum) -> str:
    """Normalize a categorical param to its stored text.

    Accepts a plain string or a `(str, Enum)` member. ``str()`` on a
    ``(str, Enum)`` yields ``"ClassName.member"`` (Enum's ``__str__``), so the
    enum value is read explicitly to match the SQL CHECK constraints.
    """
    return value.value if isinstance(value, Enum) else str(value)


def add_item(
    conn: sqlite3.Connection,
    *,
    title: str,
    start_time: str | None,
    end_time: str | None,
    duration_estimate: int | None,
    min_duration: int | None = None,
    location: str | None = None,
    status: str = "scheduled",
    type_id: int | None = None,
    commitment: str = "solo",
    counterparty_id: int | None = None,
    temporal_class: str = "anytime",
    deadline: str | None = None,
    stakes: str = "reschedulable",
    divisibility: str = "atomic",
) -> int:
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO items (
            title, start_time, end_time, duration_estimate, min_duration,
            location, status, type_id, commitment, counterparty_id,
            temporal_class, deadline, stakes, divisibility,
            version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            title, start_time, end_time, duration_estimate, min_duration,
            location, _text(status), type_id, _text(commitment), counterparty_id,
            _text(temporal_class), deadline, _text(stakes), _text(divisibility),
            now, now,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_item(conn: sqlite3.Connection, item_id: int) -> Item | None:
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return Item.from_row(row) if row else None


def set_type(conn: sqlite3.Connection, item_id: int, type_id: int) -> None:
    conn.execute(
        "UPDATE items SET type_id = ?, version = version + 1, updated_at = ? WHERE id = ?",
        (type_id, _now(), item_id),
    )
    conn.commit()


def set_status(conn: sqlite3.Connection, item_id: int, status: str) -> None:
    conn.execute(
        "UPDATE items SET status = ?, version = version + 1, updated_at = ? WHERE id = ?",
        (status, _now(), item_id),
    )
    conn.commit()


def list_in_range(conn: sqlite3.Connection, start: str, end: str) -> list[Item]:
    rows = conn.execute(
        """
        SELECT * FROM items
        WHERE start_time IS NOT NULL AND start_time < ? AND end_time > ?
        ORDER BY start_time
        """,
        (end, start),
    ).fetchall()
    return [Item.from_row(r) for r in rows]


def list_open_deadline_items(conn: sqlite3.Connection) -> list[Item]:
    rows = conn.execute(
        """
        SELECT * FROM items
        WHERE deadline IS NOT NULL AND status IN ('scheduled', 'in_progress')
        ORDER BY deadline
        """
    ).fetchall()
    return [Item.from_row(r) for r in rows]


def set_scores(conn: sqlite3.Connection, item_id: int, rigidity: float, protection: float) -> None:
    conn.execute(
        "UPDATE items SET rigidity_score = ?, protection_score = ?, updated_at = ? WHERE id = ?",
        (rigidity, protection, _now(), item_id),
    )
    conn.commit()


_FACTOR_COLUMNS = {
    "commitment", "counterparty_id", "temporal_class", "deadline", "stakes", "divisibility",
}

_CATEGORICAL_FACTOR_COLUMNS = {"commitment", "temporal_class", "stakes", "divisibility"}


def set_factors(conn: sqlite3.Connection, item_id: int, **factors) -> None:
    cols = {
        k: (_text(v) if k in _CATEGORICAL_FACTOR_COLUMNS else v)
        for k, v in factors.items()
        if k in _FACTOR_COLUMNS
    }
    if not cols:
        return
    assignments = ", ".join(f"{k} = ?" for k in cols)
    conn.execute(
        f"UPDATE items SET {assignments}, version = version + 1, updated_at = ? WHERE id = ?",
        (*cols.values(), _now(), item_id),
    )
    conn.commit()


def set_duration_estimate(conn: sqlite3.Connection, item_id: int, duration_estimate: int) -> None:
    conn.execute(
        "UPDATE items SET duration_estimate = ?, version = version + 1, updated_at = ? "
        "WHERE id = ?",
        (duration_estimate, _now(), item_id),
    )
    conn.commit()


def set_times(conn: sqlite3.Connection, item_id: int, start_time: str | None,
              end_time: str | None) -> None:
    conn.execute(
        "UPDATE items SET start_time = ?, end_time = ?, version = version + 1, updated_at = ? "
        "WHERE id = ?",
        (start_time, end_time, _now(), item_id),
    )
    conn.commit()


def set_deadline_fields(conn: sqlite3.Connection, item_id: int, deadline: str,
                        effort_estimate: int) -> None:
    conn.execute(
        "UPDATE items SET deadline = ?, effort_estimate = ?, temporal_class = 'deadline', "
        "version = version + 1, updated_at = ? WHERE id = ?",
        (deadline, effort_estimate, _now(), item_id),
    )
    conn.commit()


def add_reserved_session(conn: sqlite3.Connection, *, parent_item_id: int, title: str,
                         start_time: str, end_time: str, goal_id: int | None = None) -> int:
    now = _now()
    cur = conn.execute(
        "INSERT INTO items (title, start_time, end_time, duration_estimate, min_duration, "
        "status, temporal_class, divisibility, auto_reserved, parent_item_id, goal_id, "
        "version, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,1,?,?,1,?,?)",
        (title, start_time, end_time,
         int((parse_iso(end_time) - parse_iso(start_time)).total_seconds() // 60),
         15, "scheduled", "anytime", "divisible", parent_item_id, goal_id, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def add_series_instance(conn: sqlite3.Connection, *, series_id: int, type_id: int | None,
                        title: str, start_time: str, end_time: str, location: str | None,
                        commitment: str, counterparty_id: int | None, temporal_class: str,
                        stakes: str, divisibility: str, duration_estimate: int) -> int:
    now = _now()
    cur = conn.execute(
        "INSERT INTO items (title, start_time, end_time, duration_estimate, min_duration, "
        "location, status, type_id, commitment, counterparty_id, temporal_class, stakes, "
        "divisibility, series_id, version, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
        (title, start_time, end_time, duration_estimate, duration_estimate, location,
         "scheduled", type_id, _text(commitment), counterparty_id, _text(temporal_class),
         _text(stakes), _text(divisibility), series_id, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def set_detached(conn: sqlite3.Connection, item_id: int) -> None:
    conn.execute(
        "UPDATE items SET detached = 1, updated_at = ? WHERE id = ?", (_now(), item_id)
    )
    conn.commit()


def delete_future_series(conn: sqlite3.Connection, series_id: int, after: str) -> int:
    cur = conn.execute(
        "DELETE FROM items WHERE series_id = ? AND detached = 0 AND status = 'scheduled' "
        "AND start_time > ?",
        (series_id, after),
    )
    conn.commit()
    return cur.rowcount


def set_project(conn: sqlite3.Connection, item_id: int, project_id: int) -> None:
    conn.execute("UPDATE items SET project_id = ?, updated_at = ? WHERE id = ?",
                 (project_id, _now(), item_id))
    conn.commit()


def list_by_project(conn: sqlite3.Connection, project_id: int) -> list:
    rows = conn.execute("SELECT * FROM items WHERE project_id = ?", (project_id,)).fetchall()
    from pepper.domain.item import Item
    return [Item.from_row(r) for r in rows]
