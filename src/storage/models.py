from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse


@dataclass(frozen=True)
class NewsArticle:
    source: str
    title: str
    url: str
    published_at: datetime | None
    origin: str
    language: str | None = None

    def normalize(self) -> "NewsArticle":
        normalized_source = self.source.strip() or _domain_from_url(self.url)
        normalized_title = self.title.strip() or self.url
        normalized_url = self.url.strip()
        normalized_language = self.language.strip() if self.language else None
        return NewsArticle(
            source=normalized_source,
            title=normalized_title,
            url=normalized_url,
            published_at=self.published_at,
            origin=self.origin,
            language=normalized_language,
        )

    def content_hash(self) -> str:
        key = self.url.strip() if self.url.strip() else self.title.strip().lower()
        return sha256(key.encode("utf-8")).hexdigest()

    def as_row(self) -> dict[str, object]:
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "collected_at": datetime.now(timezone.utc),
            "origin": self.origin,
            "language": self.language,
            "hash": self.content_hash(),
        }


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or "unknown"
