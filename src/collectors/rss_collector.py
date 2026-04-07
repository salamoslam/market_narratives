from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from src.storage.models import NewsArticle
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def collect_rss_articles(feed_urls: list[str] | tuple[str, ...]) -> list[NewsArticle]:
    articles: list[NewsArticle] = []
    for feed_url in feed_urls:
        parsed_feed = feedparser.parse(feed_url)
        source = parsed_feed.feed.get("title", feed_url)
        for entry in parsed_feed.entries:
            url = str(entry.get("link", "")).strip()
            if not url:
                continue
            title = str(entry.get("title", "")).strip() or url
            published_at = _parse_datetime(entry.get("published"))
            article = NewsArticle(
                source=source,
                title=title,
                url=url,
                published_at=published_at,
                origin="rss",
                language=entry.get("language"),
            ).normalize()
            articles.append(article)
    return articles


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text_value = str(value)
    try:
        return parsedate_to_datetime(text_value)
    except (TypeError, ValueError):
        return None

def clean_url(u: str) -> str:
    parts = urlsplit(u)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "traffic_source"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))

