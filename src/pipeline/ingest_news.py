from __future__ import annotations

from src.collectors.gdelt_collector import collect_gdelt_articles
from src.collectors.rss_collector import collect_rss_articles
from src.config import get_settings
from src.storage.database import Database
from src.storage.models import NewsArticle


def run_ingestion() -> dict[str, int]:
    settings = get_settings()
    rss_articles = collect_rss_articles(settings.rss_feeds)
    gdelt_articles = collect_gdelt_articles(max_rows=settings.gdelt_max_rows)
    normalized = normalize_articles(rss_articles + gdelt_articles)
    deduped = deduplicate_articles(normalized)

    db = Database(settings.postgres_dsn)
    inserted = db.upsert_articles(deduped)

    return {
        "rss_collected": len(rss_articles),
        "gdelt_collected": len(gdelt_articles),
        "normalized": len(normalized),
        "deduplicated": len(deduped),
        "inserted": inserted,
    }


def normalize_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    return [article.normalize() for article in articles if article.url.strip()]


def deduplicate_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    deduped_by_hash: dict[str, NewsArticle] = {}
    for article in articles:
        deduped_by_hash[article.content_hash()] = article
    return list(deduped_by_hash.values())
