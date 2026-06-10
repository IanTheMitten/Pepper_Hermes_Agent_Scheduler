import pytest

from pepper.db.connection import get_connection
from pepper.db.migrations import migrate


@pytest.fixture(autouse=True)
def _reset_hermes_registry():
    from pepper.integration import hermes
    hermes.reset()
    yield
    hermes.reset()


@pytest.fixture
def conn(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("PEPPER_DB_PATH", str(db))
    connection = get_connection()
    migrate(connection)
    yield connection
    connection.close()
