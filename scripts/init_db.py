from __future__ import annotations

from src.config import get_settings
from src.storage.database import Database


def main() -> None:
    settings = get_settings()
    db = Database(settings.postgres_dsn)
    db.ensure_schema()
    print("Database schema initialized.")


if __name__ == "__main__":
    main()
