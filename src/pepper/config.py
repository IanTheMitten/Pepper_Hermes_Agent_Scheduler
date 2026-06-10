from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".pepper" / "pepper.db"


def db_path() -> Path:
    """Resolve the SQLite path, honoring the PEPPER_DB_PATH override."""
    return Path(os.environ.get("PEPPER_DB_PATH", str(DEFAULT_DB_PATH)))
