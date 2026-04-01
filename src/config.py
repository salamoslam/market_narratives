from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    postgres_db: str = os.getenv("POSTGRES_DB", "narratives")
    postgres_user: str = os.getenv("POSTGRES_USER", "narratives")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "narratives")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    rss_feeds: tuple[str, ...] = tuple(
        feed.strip()
        for feed in os.getenv("RSS_FEEDS", "").split(",")
        if feed.strip()
    )
    gdelt_max_rows: int = int(os.getenv("GDELT_MAX_ROWS", "1000"))

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
