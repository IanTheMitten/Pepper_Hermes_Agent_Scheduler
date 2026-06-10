from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply any *.sql migrations not yet recorded. Returns names newly applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    conn.commit()
    applied = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    newly: list[str] = []
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if sql_file.name in applied:
            continue
        conn.executescript(sql_file.read_text())
        conn.execute(
            "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
            (sql_file.name, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        newly.append(sql_file.name)
    return newly
