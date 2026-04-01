from __future__ import annotations

from typing import Iterable
from uuid import UUID

import psycopg
from pgvector.psycopg import register_vector

from src.storage.models import NewsArticle


DDL_NEWS_ARTICLES = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    origin TEXT NOT NULL CHECK (origin IN ('rss', 'gdelt')),
    language TEXT,
    hash TEXT NOT NULL UNIQUE,
    embedding VECTOR(1536)
);

CREATE INDEX IF NOT EXISTS idx_news_articles_published_at ON news_articles (published_at);
CREATE INDEX IF NOT EXISTS idx_news_articles_origin ON news_articles (origin);
"""


class Database:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _connect(self) -> psycopg.Connection:
        conn = psycopg.connect(self.dsn, autocommit=True)
        register_vector(conn)
        return conn

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(DDL_NEWS_ARTICLES)

    def upsert_articles(self, articles: Iterable[NewsArticle]) -> int:
        rows = [article.as_row() for article in articles]
        if not rows:
            return 0

        query = """
        INSERT INTO news_articles (
            source, title, url, published_at, collected_at, origin, language, hash
        )
        VALUES (
            %(source)s, %(title)s, %(url)s, %(published_at)s, %(collected_at)s,
            %(origin)s, %(language)s, %(hash)s
        )
        ON CONFLICT (hash) DO NOTHING;
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, rows)
                return cur.rowcount or 0

    def fetch_latest_articles(self, limit: int = 50) -> list[dict[str, object]]:
        query = """
        SELECT id, source, title, url, published_at, collected_at, origin, language, hash
        FROM news_articles
        ORDER BY collected_at DESC
        LIMIT %s;
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                columns = [c.name for c in cur.description]
                return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]

    def fetch_article_ids(self, limit: int = 10) -> list[UUID]:
        query = "SELECT id FROM news_articles ORDER BY collected_at DESC LIMIT %s;"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                return [row[0] for row in cur.fetchall()]
