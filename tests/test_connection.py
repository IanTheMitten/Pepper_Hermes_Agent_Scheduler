from pepper.db.connection import get_connection


def test_connection_enables_foreign_keys(tmp_path):
    conn = get_connection(tmp_path / "c.db")
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_connection_uses_row_factory(tmp_path):
    conn = get_connection(tmp_path / "c.db")
    try:
        row = conn.execute("SELECT 1 AS one").fetchone()
        assert row["one"] == 1
    finally:
        conn.close()
