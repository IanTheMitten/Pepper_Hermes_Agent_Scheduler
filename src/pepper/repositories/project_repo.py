from __future__ import annotations

from datetime import datetime, timezone


def create(conn, title, *, deadline=None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO projects (title, deadline, status, created_at, updated_at) "
        "VALUES (?,?,'active',?,?)",
        (title, deadline, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn, project_id):
    return conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
