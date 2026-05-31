import os
import gzip
import json
import requests
import re
from urllib.parse import urlparse
from pathlib import Path

from warcio.archiveiterator import ArchiveIterator
import trafilatura
from tqdm import tqdm
import random

from collections import defaultdict
from time import perf_counter
import langid
import hashlib

from src.config import get_settings
from concurrent.futures import ProcessPoolExecutor, as_completed

settings = get_settings()
BASE_URL = settings.ccnews_base_url

def domain_allowed(url, allowed_domains):
    domain = urlparse(url).netloc.lower()
    for d in allowed_domains:
        if domain == d or domain.endswith("." + d) or d in domain:
            return True
    return False


def url_is_article(url, bad_paths):
    for p in bad_paths:
        if p in url:
            return False
    return True


def load_processed(processed_log):
    if os.path.exists(processed_log):
        with open(processed_log) as f:
            return set(json.load(f))
    return set()


def save_processed(processed, processed_log):
    with open(processed_log, "w") as f:
        json.dump(list(processed), f)


def load_month_paths(base_url, month):
    url = f"{base_url}crawl-data/CC-NEWS/{month}/warc.paths.gz"
    r = requests.get(url)
    paths = gzip.decompress(r.content).decode().splitlines()
    random.shuffle(paths)
    return paths

def parse_extracted_article(
    extracted,
    *,
    min_text_len=500,
    allowed_langs=("en", "ru"),
    lang_sample_chars=500,
):
    stats_delta = {
        "extract_non_empty": 0,
        "json_errors": 0,
        "lang_errors": 0,
        "lang_filtered_out": 0,
    }

    if not extracted:
        return None, stats_delta

    stats_delta["extract_non_empty"] = 1

    try:
        data = json.loads(extracted)
    except Exception:
        stats_delta["json_errors"] = 1
        stats_delta["extract_non_empty"] = 0
        return None, stats_delta

    text = data.get("text")
    if not text or len(text) < min_text_len:
        return None, stats_delta

    try:
        lang = langid.classify(f"{data.get('title') or ''} {text[:lang_sample_chars]}")[0]
    except Exception:
        stats_delta["lang_errors"] = 1
        return None, stats_delta

    if lang not in set(allowed_langs):
        stats_delta["lang_filtered_out"] = 1
        return None, stats_delta

    return {"data": data, "text": text, "lang": lang}, stats_delta

def process_warc_stream(
    url,
    output_file,
    *,
    bad_paths,
    max_html_size,
    write_batch_size,
    max_items_per_warc,
    downsample_rate=None,
    min_text_len=500,
    allowed_domains=None,
    allowed_langs=("en", "ru"),
):
    t_warc_start = perf_counter()
    stats = defaultdict(float)
    write_buffer = []

    r = requests.get(url, stream=True)
    stream = gzip.GzipFile(fileobj=r.raw)

    for record in ArchiveIterator(stream):
        stats["records_seen"] += 1

        if record.rec_type != "response":
            continue

        stats["response_records"] += 1
        record_url = record.rec_headers.get_header("WARC-Target-URI")

        if not record_url:
            continue

        if not url_is_article(record_url, bad_paths):
            continue

        if allowed_domains and not domain_allowed(record_url, allowed_domains):
            continue

        stats["after_url_filters"] += 1
        html = record.content_stream().read()

        if len(html) > max_html_size:
            continue

        stats["after_size_filter"] += 1

        t_extract_start = perf_counter()
        extracted = trafilatura.extract(
            html,
            output_format="json",
            with_metadata=True
        )
        stats["extract_seconds"] += perf_counter() - t_extract_start

        parsed, d = parse_extracted_article(
            extracted,
            min_text_len=min_text_len,
            allowed_langs=allowed_langs,
            lang_sample_chars=500,
        )
        for k, v in d.items():
            stats[k] += v
        if not parsed:
            continue

        data, text, lang = parsed["data"], parsed["text"], parsed["lang"]

        item = {
            "url": record_url,
            "domain": urlparse(record_url).netloc.lower(),
            "title": data.get("title"),
            "date": data.get("date"),
            "author": data.get("author"),
            "lang": lang,
            "text": text,
        }

        write_buffer.append(json.dumps(item, ensure_ascii=False) + "\n")
        stats["written"] += 1

        if len(write_buffer) >= write_batch_size:
            output_file.write("".join(write_buffer))
            write_buffer.clear()

        if stats["written"] >= max_items_per_warc:
            stats["stopped_by_limit"] = 1
            break

    if write_buffer:
        output_file.write("".join(write_buffer))

    stats["warc_seconds"] = perf_counter() - t_warc_start
    return stats


def run_one_warc(warc_url, cfg):
    match = re.search(r"crawl-data/CC-NEWS/(\d{4})/(\d{2})/(.+)$", warc_url)
    if match:
        year, month, warc_tail = match.groups()
    else:
        year, month, warc_tail = "unknown", "unknown", Path(warc_url).name

    output_root = cfg["output_root"]
    out_dir = Path(output_root) / year / month
    out_dir.mkdir(parents=True, exist_ok=True)

    warc_name = Path(warc_tail).name.replace(".warc.gz", ".jsonl")
    output_path = out_dir / warc_name

    with open(output_path, "a", encoding="utf-8") as out:
        stats = process_warc_stream(
            warc_url,
            out,
            bad_paths=cfg["bad_paths"],
            max_html_size=cfg["max_html_size"],
            write_batch_size=cfg["write_batch_size"],
            max_items_per_warc=cfg["max_items_per_warc"],
            downsample_rate=cfg["downsample_rate"],
            allowed_domains=cfg["allowed_domains"],
            allowed_langs=cfg["allowed_langs"],
        )
    return {"warc_url": warc_url, "output_path": str(output_path), "stats": dict(stats)}


def warc_already_done(conn, warc_path: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM raw.ccnews_warc_checkpoint WHERE warc_path = %s AND status = 'done' LIMIT 1",
            (warc_path,),
        )
        return cur.fetchone() is not None


def mark_warc_done(conn, warc_path: str, month: str, rows_written: int, rows_inserted: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.ccnews_warc_checkpoint (warc_path, month, status, rows_written, rows_inserted, updated_at)
            VALUES (%s, %s, 'done', %s, %s, now())
            ON CONFLICT (warc_path) DO UPDATE
            SET status = EXCLUDED.status,
                rows_written = EXCLUDED.rows_written,
                rows_inserted = EXCLUDED.rows_inserted,
                updated_at = now()
            """,
            (warc_path, month, rows_written, rows_inserted),
        )


def run_ccnews_month(
    *,
    month: str,
    output_root: str = "/opt/airflow/project/data/raw/ccnews",
    max_workers: int = 4,
    max_warcs: int | None = None,
    allowed_domains: set[str],
    bad_paths: list[str],
    max_html_size: int = 1_000_000,
    write_batch_size: int = 200,
    max_items_per_warc: int = 100000,
    downsample_rate: float | None = None,
    allowed_langs: tuple[str, ...] = ("en", "ru"),
) -> dict:

    BASE_URL = "https://data.commoncrawl.org/"
    out_root = Path(output_root)
    out_root.mkdir(parents=True, exist_ok=True)
    processed_log = out_root / month / "_processed_warcs.json"
    processed_log.parent.mkdir(parents=True, exist_ok=True)
    cfg = {
        "bad_paths": bad_paths,
        "max_html_size": max_html_size,
        "write_batch_size": write_batch_size,
        "max_items_per_warc": max_items_per_warc,
        "downsample_rate": downsample_rate,
        "allowed_domains": allowed_domains,
        "allowed_langs": allowed_langs,
        "output_root": str(out_root),
    }
    processed = load_processed(str(processed_log))
    warc_rels = load_month_paths(BASE_URL, month)
    random.shuffle(warc_rels)
    warc_rels = [w for w in warc_rels if w not in processed]
    if max_warcs is not None:
        warc_rels = warc_rels[:max_warcs]
    total = defaultdict(float)
    t0 = perf_counter()
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        future_map = {
            ex.submit(run_one_warc, BASE_URL + warc_rel, cfg): warc_rel
            for warc_rel in warc_rels
        }
        for fut in as_completed(future_map):
            warc_rel = future_map[fut]
            try:
                res = fut.result()
                stats = res["stats"]
                for k, v in stats.items():
                    total[k] += v
                processed.add(warc_rel)
                save_processed(processed, str(processed_log))
            except Exception:
                pass
    elapsed = perf_counter() - t0
    return {
        "month": month,
        "warcs_total": len(warc_rels),
        "written": int(total.get("written", 0)),
        "records_seen": int(total.get("records_seen", 0)),
        "extract_seconds": float(total.get("extract_seconds", 0)),
        "elapsed_seconds": elapsed,
    }