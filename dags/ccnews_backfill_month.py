from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.decorators import task

from src.config import get_settings
from src.collectors.ccnews_extractor import (
    load_month_paths,
    load_processed,
    save_processed,
    run_one_warc,
)
from src.pipeline.load_ingest_to_db import ingest_ccnews_jsonl_file


BAD_PATHS = [
    "/video/",
    "/videos/",
    "/live/",
    "/gallery/",
    "/podcast/",
    "sport",
    "crimea",
]


with DAG(
    dag_id="ccnews_month_backfill",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["ccnews", "backfill"],
) as dag:

    @task
    def extract_and_load_month(**context) -> dict:
        conf = (context.get("dag_run").conf or {})

        month = conf.get("month")
        if not month:
            raise ValueError("Provide month in dag_run.conf, example: {'month':'2025/09'}")

        settings = get_settings()

        base_url = conf.get("base_url", "https://data.commoncrawl.org/")
        output_root = conf.get("output_root", "/opt/airflow/project/data/raw/ccnews")
        max_warcs = conf.get("max_warcs")
        max_warcs = int(max_warcs) if max_warcs is not None else None

        cfg = {
            "bad_paths": conf.get("bad_paths", BAD_PATHS),
            "max_html_size": int(conf.get("max_html_size", 1_000_000)),
            "write_batch_size": int(conf.get("write_batch_size", 200)),
            "max_items_per_warc": int(conf.get("max_items_per_warc", 100_000)),
            "downsample_rate": conf.get("downsample_rate"),
            "allowed_domains": set(conf.get("allowed_domains", list(settings.allowed_domains))),
            "allowed_langs": tuple(conf.get("allowed_langs", ["en", "ru"])),
            "output_root": output_root,
        }

        month_dir = Path(output_root) / month
        month_dir.mkdir(parents=True, exist_ok=True)
        processed_log = month_dir / "_processed_warcs.json"

        processed = load_processed(str(processed_log))
        warc_rels = load_month_paths(base_url, month)
        warc_rels = [w for w in warc_rels if w not in processed]
        if max_warcs is not None:
            warc_rels = warc_rels[:max_warcs]

        total_inserted = 0
        total_written = 0
        failed = 0

        for warc_rel in warc_rels:
            try:
                # 1) Extract one WARC to disk (jsonl file)
                res = run_one_warc(base_url + warc_rel, cfg)
                output_path = res["output_path"]

                # 2) Load that jsonl file into news_articles
                db_stats = ingest_ccnews_jsonl_file(
                    output_path,
                    dsn=settings.postgres_dsn,
                    source_type="ccnews",
                    verbose=False,
                )

                total_inserted += int(db_stats.get("inserted_estimate", 0))
                total_written += int(res.get("stats", {}).get("written", 0))

                # 3) Mark this WARC as processed only after successful DB load
                processed.add(warc_rel)
                save_processed(processed, str(processed_log))

                print(
                    f"WARC_DONE warc={warc_rel} "
                    f"written={int(res.get('stats', {}).get('written', 0))} "
                    f"inserted={int(db_stats.get('inserted_estimate', 0))} "
                    f"out={output_path}"
                )
            except Exception as e:
                failed += 1
                print(f"WARC_FAILED warc={warc_rel} error={e}")

        return {
            "month": month,
            "warcs_total": len(warc_rels),
            "written_total": total_written,
            "inserted_total": total_inserted,
            "failed": failed,
            "processed_log": str(processed_log),
        }

    extract_and_load_month()