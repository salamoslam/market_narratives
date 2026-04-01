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

        if not extracted:
            continue

        stats["extract_non_empty"] += 1

        t_json_start = perf_counter()
        try:
            data = json.loads(extracted)
        except Exception:
            stats["json_errors"] += 1
            continue
        stats["json_seconds"] += perf_counter() - t_json_start

        text = data.get("text")

        if not text or len(text) < min_text_len:
            continue

        try:
            lang = langid.classify(f"{data.get('title') or ''} {text[:500]}")[0]
        except Exception:
            lang = None
            stats["lang_errors"] += 1

        if lang not in set(allowed_langs):
            stats["lang_filtered_out"] += 1
            continue

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