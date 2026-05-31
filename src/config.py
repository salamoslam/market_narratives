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
    ccnews_base_url: str = os.getenv("CCNEWS_BASE_URL", "https://data.commoncrawl.org/")
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
    rss_feeds: tuple[str, ...] = tuple([
        "https://www.aljazeera.com/xml/rss/all.xml",
        # "https://feeds.bbci.co.uk/news/world/rss.xml",
        # "https://feeds.bbci.co.uk/news/business/rss.xml",
        # "https://feeds.bbci.co.uk/news/politics/rss.xml",
        # "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "http://feeds.bbci.co.uk/news/rss.xml",

        "https://www.theguardian.com/world/rss",

        "https://www.independent.co.uk/news/world/rss",
        "https://www.independent.co.uk/news/business/rss",
        "https://www.independent.co.uk/news/science/rss",

        "https://www.kommersant.ru/rss/section-politics.xml",
        "https://www.kommersant.ru/rss/section-world.xml",
        "https://www.kommersant.ru/rss/section-business.xml",
        "https://www.kommersant.ru/rss/section-society.xml",

        # newindianexpress.com        |   41517
        # the-independent.com         |   38655
        # cbsnews.com                 |   38472
        # independent.co.uk           |   31192
        # allafrica.com               |   26494
        # interfax.ru                 |   18925
        # vedomosti.ru                |   18217
        # ndtv.com                    |   16847
        # foxnews.com                 |   16370
        # rbc.ru                      |   15284
        # zakon.kz                    |   14761
        # channelnewsasia.com         |   13023
        # lenta.ru                    |   12715
        # latimes.com                 |   12248
        # telegraph.co.uk             |   10970
        # nzherald.co.nz              |   10536
        # globalnews.ca               |    9790
        # irishtimes.com              |    9782
        # thewest.com.au              |    9571
        # ctvnews.ca                  |    9553
        # yorkshirepost.co.uk         |    9402
        # tass.ru                     |    8302
        # timeslive.co.za             |    8039
        # scotsman.com                |    7302
        # aljazeera.com               |    7118
        # straitstimes.com            |    6932
        # vietnamnews.vn              |    6862
        # nur.kz                      |    6711
        # indianexpress.com           |    6503
        # thenationalnews.com         |    6490
        # businesslive.co.za          |    5804
        # abcnews.go.com              |    5624
        # qz.com                      |    4572
        # khaleejtimes.com            |    3956
        # ca.news.yahoo.com           |    3729
        # nickiswift.com              |    1305
        # ca.style.yahoo.com          |     411
        # not-qz.com                  |     293
        ]
    )

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
