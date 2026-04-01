from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime
from typing import Iterable
from urllib.parse import urlparse

import requests

from src.storage.models import NewsArticle

GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"


def collect_gdelt_articles(max_rows: int = 1000) -> list[NewsArticle]:
    export_url = _resolve_latest_export_url()
    if not export_url:
        return []

    rows = _download_export_rows(export_url, max_rows=max_rows)
    articles: list[NewsArticle] = []

    for row in rows:
        url = row[57].strip() if len(row) > 57 else ""
        if not url:
            continue

        source = _extract_source(url)
        published_at = _parse_gdelt_timestamp(row[1] if len(row) > 1 else "")
        themes = row[7].strip() if len(row) > 7 else ""
        language = _extract_language_from_themes(themes)

        article = NewsArticle(
            source=source,
            title=url,
            url=url,
            published_at=published_at,
            origin="gdelt",
            language=language,
        ).normalize()
        articles.append(article)

    return articles


def _resolve_latest_export_url() -> str | None:
    response = requests.get(GDELT_LAST_UPDATE_URL, timeout=30)
    response.raise_for_status()
    for line in response.text.splitlines():
        parts = line.strip().split(" ")
        if len(parts) < 3:
            continue
        candidate_url = parts[2].strip()
        if candidate_url.endswith(".export.CSV.zip"):
            return candidate_url
    return None


def _download_export_rows(export_url: str, max_rows: int) -> Iterable[list[str]]:
    response = requests.get(export_url, timeout=120)
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    filename = archive.namelist()[0]
    with archive.open(filename) as file_obj:
        decoded = io.TextIOWrapper(file_obj, encoding="utf-8", errors="replace")
        reader = csv.reader(decoded, delimiter="\t")
        for idx, row in enumerate(reader):
            if idx >= max_rows:
                break
            yield row


def _parse_gdelt_timestamp(value: str) -> datetime | None:
    raw = value.strip()
    if not raw:
        return None
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _extract_source(url: str) -> str:
    return urlparse(url).netloc or "unknown"


def _extract_language_from_themes(themes: str) -> str | None:
    for token in themes.split(";"):
        token = token.strip()
        if token.startswith("LANGUAGE_"):
            return token.replace("LANGUAGE_", "").lower()
    return None
