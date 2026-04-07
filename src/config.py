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
    allowed_domains: tuple[str, ...] = tuple([
        "reuters.com",
        "bbc.com",
        "bbc.co.uk",
        "ft.com",
        "bloomberg.com",
        "cnbc.com",
        "wsj.com",
        "nytimes.com",
        "economist.com",
        "theguardian.com",
        "washingtonpost.com",
        "apnews.com",
        "businessinsider.com",
        "marketwatch.com",
        "yahoo.com",
        "forbes.com",
        "cnn.com",
        "nbcnews.com",
        "abcnews.go.com",
        "aljazeera.com",
        "www.channelnewsasia.com",
        "www.thenationalnews.com",
        "www.straitstimes.com",
        "vietnamnews.vn",
        "abcnews.go.com",
        "www.cbsnews.com",
        "www.foxnews.com",
        "www.latimes.com",
        "globalnews.ca",
        "www.ctvnews.ca",
        "www.telegraph.co.uk",
        "www.independent.co.uk",
        "www.the-independent.com",
        "www.irishtimes.com",
        "www.scotsman.com",
        "www.yorkshirepost.co.uk",
        "indianexpress.com",
        "www.ndtv.com",
        "gulfnews.com",
        "www.khaleejtimes.com",
        "allafrica.com",
        "www.timeslive.co.za",
        "www.businesslive.co.za",
        "thewest.com.au",
        "www.nzherald.co.nz",
        "qz.com",
        "www.tass.ru",
        "www.interfax.ru",
        "www.rbc.ru",
        "www.vedomosti.ru",
        "www.kommersant.ru",
        "www.lenta.ru",
        "www.nur.kz",
        "www.zakon.kz"]
    )

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
