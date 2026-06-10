from pepper.db.migrations import migrate


def _table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r["name"] for r in rows}


def test_migrate_creates_core_tables(conn):
    names = _table_names(conn)
    assert {"items", "persons", "schema_migrations"} <= names


def test_migrate_is_idempotent(conn):
    # `conn` fixture already migrated once; a second run applies nothing new.
    assert migrate(conn) == []


def test_items_enforces_status_check(conn):
    import sqlite3

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO items (title, status, commitment, temporal_class, stakes, "
            "divisibility, version, created_at, updated_at) "
            "VALUES ('x', 'bogus', 'solo', 'anytime', 'reschedulable', 'atomic', 1, '', '')"
        )
