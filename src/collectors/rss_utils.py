from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit
import asyncio
import json
import os
import random
import time

import feedparser
import langid
import pandas as pd
import requests
import trafilatura
from tqdm import tqdm
from playwright.async_api import async_playwright

from src.storage.models import NewsArticle
from src.collectors.ccnews_extractor import parse_extracted_article

from hashlib import sha256
import psycopg
from src.config import get_settings


OUT_ROOT = str(Path(__file__).resolve().parents[2] / "data" / "raw" / "rss")

def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text_value = str(value)
    try:
        return parsedate_to_datetime(text_value)
    except (TypeError, ValueError):
        return None

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



def clean_url(u: str) -> str:
    parts = urlsplit(u)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "traffic_source"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


async def google_news_resolve_many(
    urls,
    timeout_ms=15000,
    min_delay_s=0.4,
    max_delay_s=1.1,
    max_retries=2,
):
    ## not used anymore
    out = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="en-US",
        )
        page = await context.new_page()

        for i, u in enumerate(urls, 1):
            result = None

            for attempt in range(max_retries + 1):
                try:
                    # human-like pacing before each navigation
                    # await asyncio.sleep(random.uniform(min_delay_s, max_delay_s))
                    await page.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
                    await page.wait_for_timeout(1000)

                    # small post-load jitter for JS redirects
                    await asyncio.sleep(random.uniform(min_delay_s, max_delay_s))

                    result = page.url
                    break
                except Exception:
                    if attempt < max_retries:
                        # backoff + jitter before retry
                        await asyncio.sleep((attempt + 1) * random.uniform(min_delay_s, max_delay_s))
                    else:
                        result = None

            out[u] = result
            print(f"[{i}/{len(urls)}] resolved={result is not None}, url={u}, result={result}")

        await context.close()
        await browser.close()

    return out


def _month_partition_path(base_dir: str, item_date: str | None) -> str:
    dt = pd.to_datetime(item_date, errors="coerce")
    if pd.isna(dt):
        dt = pd.Timestamp.utcnow()
    year = f"{dt.year:04d}"
    month = f"{dt.month:02d}"
    out_dir = os.path.join(base_dir, year, month)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, "articles.jsonl")


def get_resolved_urls(rss_url: str, rows: list[tuple[str, str, str]]) -> list[str]:
    settings = get_settings()
    with psycopg.connect(settings.postgres_dsn) as conn:
        with conn.cursor() as cur:
            print(f"[DB_START] feed={rss_url}")
            cur.execute("DROP TABLE IF EXISTS tmp_rss_candidates")
            cur.execute(
                """
                CREATE TEMP TABLE tmp_rss_candidates (
                    article_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    rss_url TEXT NOT NULL
                ) ON COMMIT DROP
                """
            )
            print(f"[DB_INSERT] feed={rss_url} rows={len(rows)}")
            cur.executemany(
                """
                INSERT INTO tmp_rss_candidates (article_id, url, rss_url)
                VALUES (%s, %s, %s)
                ON CONFLICT (article_id) DO NOTHING
                """,
                rows,
            )
            print(f"[DB_SELECT] feed={rss_url}")
            cur.execute(
                """
                SELECT c.url
                FROM tmp_rss_candidates c
                LEFT JOIN news_articles n
                ON n.article_id = c.article_id
                WHERE n.article_id IS NULL
                """
            )

            resolved_urls = [r[0] for r in cur.fetchall()]
            print(f"[DB_FETCH_END] feed={rss_url} resolved_urls={len(resolved_urls)}")
    
    return resolved_urls


def fetch_with_retry(session, url, request_timeout=20, max_retries=3, max_wait_s=12):
    for attempt in range(max_retries + 1):
        try:
            r = session.get(url, timeout=request_timeout, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
            status = r.status_code

            if status == 429:
                ra = r.headers.get("Retry-After")
                wait_s = float(ra) if (ra and ra.isdigit()) else (2 ** attempt + random.uniform(0.3, 1.3))
                time.sleep(min(max_wait_s, wait_s))
                continue

            if status >= 500:
                time.sleep(min(max_wait_s, 2 ** attempt + random.uniform(0.3, 1.3)))
                continue

            if status >= 400:
                return None, 0, f"http_{status}"

            r.raise_for_status()
            html = r.text
            return html, status, None

        except requests.Timeout:
            time.sleep(min(max_wait_s, 2 ** attempt + random.uniform(0.3, 1.3)))
        except requests.RequestException as ex:
            if attempt == max_retries:
                return None, status, f"request_error:{ex.__class__.__name__}"
            time.sleep(min(max_wait_s, 2 ** attempt + random.uniform(0.3, 1.3)))
        except Exception as ex:
            return None, 0, f"unexpected:{ex.__class__.__name__}"

    return None, 0, "retry_exhausted"


async def run_rss_cycle(
    rss_urls,
    *,
    max_items=200,
    min_text_len=500,
    allowed_langs=("en", "ru"),
    request_timeout=30,
    out_root=OUT_ROOT
):

    stats = {
        "feeds": len(rss_urls),
        "rss_entries": 0,
        "fetched_ok": 0,
        "extract_non_empty": 0,
        "json_errors": 0,
        "lang_errors": 0,
        "lang_filtered_out": 0,
        "written": 0,
    }

    for rss_url in rss_urls:

        items = []
        seen_urls = set()

        feed = feedparser.parse(rss_url)
        entries = feed.entries[:max_items]
        stats["rss_entries"] += len(entries)

        urls = [clean_url(str(e.get("link", "")).strip()) for e in entries]
        rows = [(sha256(u.encode("utf-8")).hexdigest(), u, rss_url) for u in urls]
        resolved_urls = get_resolved_urls(rss_url, rows) # check if the url is already in the database

        for url in tqdm(resolved_urls, desc=f"RSS -> extract | {rss_url}"):
            print(f"[LINK_START] feed={rss_url} url={url}")
            time.sleep(random.uniform(0.5, 1.2))

            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            html, status, err = fetch_with_retry(requests, url, request_timeout=request_timeout, max_retries=3)
            if err:
                failed_urls.append((url, err))
                print(f"[LINK_FAIL] feed={rss_url} url={url} err={err}")
                continue
            else:
                stats["fetched_ok"] += 1
                print(f"[LINK_OK] feed={rss_url} url={url} status={status}")

            # try:
            #     r = requests.get(
            #         url,
            #         timeout=request_timeout,
            #         headers={"User-Agent": "Mozilla/5.0"},
            #     )
            #     r.raise_for_status()
            #     html = r.text
            #     stats["fetched_ok"] += 1
            #     print(f"[LINK_OK] feed={rss_url} url={url} status={r.status_code}")

            # except Exception as ex:
            #     print(f"[LINK_FAIL] feed={rss_url} url={url} err={ex}")
            #     continue

            extracted = trafilatura.extract(
                html,
                output_format="json",
                with_metadata=True
            )

            parsed, d = parse_extracted_article(
                extracted,
                min_text_len=min_text_len,
                allowed_langs=allowed_langs,
                lang_sample_chars=500,
            )
            if parsed:
                print(f"[LINK_EXTRACTED] feed={rss_url} url={url} parsed={parsed['text'][:200]}... d={d}")
            else:
                print(f"[LINK_EXTRACTED_FAIL] feed={rss_url} url={url} parsed={parsed} d={d}")

            for k, v in d.items():
                stats[k] = stats.get(k, 0) + v
            if not parsed:
                continue

            data, text, lang = parsed["data"], parsed["text"], parsed["lang"]
            item = {
                "url": url,
                "domain": urlparse(url).netloc.lower(),
                "title": data.get("title"),
                "date": data.get("date"),
                "author": data.get("author"),
                "lang": lang,
                "text": text,
                "rss_url": rss_url,
                "collected_at": datetime.utcnow().isoformat(),
            }
            items.append(item)

        # save partitioned by item month
        for x in items:
            out_path = _month_partition_path(out_root, x.get("date"))
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
            stats["written"] += 1

    return stats, items