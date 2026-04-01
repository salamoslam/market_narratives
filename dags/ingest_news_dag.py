from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task

from src.collectors.gdelt_collector import collect_gdelt_articles
from src.collectors.rss_collector import collect_rss_articles
from src.config import get_settings
from src.pipeline.ingest_news import deduplicate_articles, normalize_articles
from src.storage.database import Database


@dag(
    dag_id="ingest_news",
    schedule="*/30 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ingestion", "news"],
)
def ingest_news_dag():
    from src.storage.models import NewsArticle

    def _to_row(article: NewsArticle) -> dict[str, str | None]:
        return {
            "source": article.source,
            "title": article.title,
            "url": article.url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "origin": article.origin,
            "language": article.language,
        }

    def _to_article(row: dict[str, str | None]) -> NewsArticle:
        published_at = (
            datetime.fromisoformat(row["published_at"])
            if row.get("published_at")
            else None
        )
        return NewsArticle(
            source=str(row["source"]),
            title=str(row["title"]),
            url=str(row["url"]),
            published_at=published_at,
            origin=str(row["origin"]),
            language=str(row["language"]) if row["language"] else None,
        )

    @task
    def collect_rss() -> list[dict[str, str | None]]:
        settings = get_settings()
        articles = collect_rss_articles(settings.rss_feeds)
        return [_to_row(article) for article in articles]

    @task
    def collect_gdelt() -> list[dict[str, str | None]]:
        settings = get_settings()
        articles = collect_gdelt_articles(max_rows=settings.gdelt_max_rows)
        return [_to_row(article) for article in articles]

    @task
    def normalize_data(
        rss_rows: list[dict[str, str | None]],
        gdelt_rows: list[dict[str, str | None]],
    ) -> list[dict[str, str | None]]:
        all_rows = rss_rows + gdelt_rows
        articles = [_to_article(row) for row in all_rows]
        normalized = normalize_articles(articles)
        deduped = deduplicate_articles(normalized)
        return [_to_row(article) for article in deduped]

    @task
    def store_articles(rows: list[dict[str, str | None]]) -> int:
        settings = get_settings()
        db = Database(settings.postgres_dsn)
        db.ensure_schema()

        articles = [_to_article(row) for row in rows]
        return db.upsert_articles(articles)

    rss = collect_rss()
    gdelt = collect_gdelt()
    normalized = normalize_data(rss, gdelt)
    store_articles(normalized)


ingest_news_dag()
