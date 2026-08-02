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
    bad_url_patterns: tuple[str, ...] = (
        "/video/",
        "/videos/",
        "/audio/",
        "/live/",
        "/gallery/",
        "/podcast/",
        "/specials/",
        "sport",
        "crimea",
    )
    publisher_domain_groups: tuple[tuple[str, ...], ...] = (
        ("bbc.co.uk", "bbc.com", "bbci.co.uk"),
    )
    rss_proxy_feed_hosts: tuple[str, ...] = (
        "feeds.feedburner.com",
    )
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
        "www.zakon.kz",
        "france24.com",
        "dw.com",
        "euronews.com",
        "npr.org",
        "foreignpolicy.com",
        "thediplomat.com",
        "scmp.com",
        "arstechnica.com",
        "techcrunch.com",
        "wired.com",
        "theverge.com",
        "themoscowtimes.com",
        "meduza.io",
        "tass.com",
        "newsru.com",
        "unian.info",
        "huffpost.com",
        "timesofindia.indiatimes.com",
        "rt.com",
        "asia.nikkei.com",
        # "rfi.fr",
        # "axios.com",
    ])

    rss_feeds: tuple[str, ...] = tuple([
        # "https://www.aljazeera.com/xml/rss/all.xml",
        # "http://feeds.bbci.co.uk/news/rss.xml",

        # "https://www.theguardian.com/world/rss",

        # "https://www.independent.co.uk/news/world/rss",
        # "https://www.independent.co.uk/news/business/rss",
        # "https://www.independent.co.uk/news/science/rss",

        # "https://www.kommersant.ru/rss/section-politics.xml",
        # "https://www.kommersant.ru/rss/section-world.xml",
        # "https://www.kommersant.ru/rss/section-business.xml",
        # "https://www.kommersant.ru/rss/section-society.xml",

        # --- global / geopolitics ---
        "http://rss.cnn.com/rss/edition_world.rss",
        "https://rss.dw.com/rdf/rss-en-world",
        # mrss feed: 50/56 extracted in 2026-07-31 test (~89%). Mostly normal text
        # articles (EU/world news); ~6 failures were video-only pages where trafilatura
        # got no body text. bad_url_patterns skips /video/ URLs upfront; remaining
        # failures are short clips or pages with no extractable article body — safe to keep.
        "https://www.euronews.com/rss?format=mrss&level=theme&name=news",
        "https://news.yahoo.com/rss/",
        "https://feeds.npr.org/1001/rss.xml",
        "https://foreignpolicy.com/feed/",
        "https://thediplomat.com/feed/",
        "https://www.cbsnews.com/latest/rss/main",
        "https://www.scmp.com/rss/91/feed",
        "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml",
        "https://www.huffpost.com/section/world-news/feed",
        "https://www.latimes.com/world-nation/rss2.0.xml",
        "http://feeds.foxnews.com/foxnews/latest",
        "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
        "https://globalnews.ca/feed/",

        "https://www.aljazeera.com/xml/rss/all.xml",
        # "https://www.rfi.fr/en/rss",
        "https://www.theguardian.com/world/rss",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "http://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://indianexpress.com/section/world/feed/",
        # "https://api.axios.com/feed/",

        "https://www.independent.co.uk/news/world/rss",
        "https://www.independent.co.uk/news/business/rss",
        "https://www.independent.co.uk/news/science/rss",

        # --- not viable (kept for reference) ---
        # "https://www.france24.com/en/rss",  # 0/23 — http_403, bot block from server IP
        # "http://feeds.washingtonpost.com/rss/world",  # 0/3 — paywall, retry_exhausted
        # "http://feeds.feedburner.com/ndtvnews-world-news",  # 0/20 — http_403, datacenter block
        # "https://rss.newsru.com/top/big/",  # feed dead since May 2021, parser ok but no new items
        # --- macro / finance ---
        "http://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.theguardian.com/business/rss",
        "https://www.businessinsider.com/rss",
        # --- tech ---
        "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.theguardian.com/technology/rss",
        "http://feeds.arstechnica.com/arstechnica/index",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        # --- russian / regional ---
        "https://www.themoscowtimes.com/rss/news",
        "https://meduza.io/rss/all",
        "https://lenta.ru/rss",
        "https://www.vedomosti.ru/rss/news",
        "https://www.interfax.ru/rss.asp",
        "http://tass.com/rss/v2.xml",
        "https://rss.unian.net/site/news_eng.rss",

        "https://www.kommersant.ru/rss/section-politics.xml",
        "https://www.kommersant.ru/rss/section-world.xml",
        "https://www.kommersant.ru/rss/section-business.xml",
        "https://www.kommersant.ru/rss/section-society.xml",
        # --- optional: state narrative lens ---
        # "https://www.rt.com/rss/",


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
