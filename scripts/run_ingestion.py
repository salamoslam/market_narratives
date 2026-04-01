from __future__ import annotations

from src.pipeline.ingest_news import run_ingestion
from src.storage.database import Database
from src.config import get_settings


def main() -> None:
    settings = get_settings()
    db = Database(settings.postgres_dsn)
    db.ensure_schema()
    stats = run_ingestion()
    print(stats)


if __name__ == "__main__":
    main()
