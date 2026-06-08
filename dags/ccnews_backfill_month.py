from __future__ import annotations

from datetime import datetime, timedelta
import psycopg
from time import perf_counter

from airflow import DAG
from airflow.decorators import task
from airflow.models.param import Param

from src.config import get_settings
from src.collectors.ccnews_extractor import (
    load_month_paths,
    run_one_warc,
    warc_already_done,
    mark_warc_done,
    mark_warc_failed,
    upsert_month_total_warcs,
    refresh_month_warc_counts,
    get_month_warc_counts,
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
    params={
        "month": Param(default="2026/01", type="string"),
        "max_warcs": Param(default=0, type="integer"),
    },
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["ccnews", "backfill"],
) as dag:

    @task
    def extract_and_load_month(**context) -> dict:
        conf = (context.get("dag_run").conf or {})
        params = (context.get("params") or {})

        month = (conf.get("month") or params.get("month") or "").strip()
        months = ([month] if month else [])
        if not months:
            raise ValueError("Provide month")

        settings = get_settings()

        base_url = conf.get("base_url", "https://data.commoncrawl.org/")
        output_root = conf.get("output_root", "/opt/airflow/project/data/raw/ccnews")
        max_warcs = conf.get("max_warcs") or params.get("max_warcs") or None
        max_warcs = int(max_warcs) if max_warcs else None

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
        print(
            f"CCNEWS_START months={months} base_url={base_url} "
            f"output_root={output_root} max_warcs={max_warcs}"
        )

        source_total_warcs = 0
        selected_total_warcs = 0
        total_inserted = 0
        total_written = 0
        failed = 0
        month_progress = {}
        skipped_done = 0

        with psycopg.connect(settings.postgres_dsn, autocommit=True) as conn:
            for month in months:
                t_month_start = perf_counter()
                print(f"MONTH_START month={month}")
                t_paths_start = perf_counter()
                all_warc_rels = load_month_paths(base_url, month)
                print(
                    f"MONTH_PATHS_LOADED month={month} total={len(all_warc_rels)} "
                    f"elapsed_sec={perf_counter() - t_paths_start:.2f}"
                )
                source_total_warcs += len(all_warc_rels)

                upsert_month_total_warcs(conn, month, len(all_warc_rels))

                warc_rels = all_warc_rels[:max_warcs] if max_warcs is not None else all_warc_rels
                selected_total_warcs += len(warc_rels)
                print(f"MONTH_SELECTED month={month} selected={len(warc_rels)}")

                for idx, warc_rel in enumerate(warc_rels, start=1):
                    if idx % 100 == 0:
                        print(
                            f"MONTH_HEARTBEAT month={month} checked={idx}/{len(warc_rels)} "
                            f"skipped_done={skipped_done} written_total={total_written} "
                            f"inserted_total={total_inserted} failed={failed}"
                        )
                    if warc_already_done(conn, warc_rel):
                        skipped_done += 1
                        continue
                    try:
                        t_warc_start = perf_counter()
                        print(f"WARC_START month={month} idx={idx}/{len(warc_rels)} warc={warc_rel}")
                        res = run_one_warc(base_url + warc_rel, cfg)
                        output_path = res["output_path"]

                        db_stats = ingest_ccnews_jsonl_file(
                            output_path,
                            dsn=settings.postgres_dsn,
                            source_type="ccnews",
                            verbose=False,
                        )

                        written = int(res.get("stats", {}).get("written", 0))
                        inserted = int(db_stats.get("inserted_estimate", 0))

                        total_written += written
                        total_inserted += inserted

                        mark_warc_done(
                            conn,
                            warc_path=warc_rel,
                            month=month,
                            rows_written=written,
                            rows_inserted=inserted,
                        )
                        print(
                            f"WARC_DONE month={month} idx={idx}/{len(warc_rels)} warc={warc_rel} "
                            f"written={written} inserted={inserted} "
                            f"elapsed_sec={perf_counter() - t_warc_start:.2f}"
                        )
                    except Exception as e:
                        failed += 1
                        mark_warc_failed(conn, warc_rel, month, str(e))
                        print(f"WARC_FAILED month={month} idx={idx}/{len(warc_rels)} warc={warc_rel} error={e}")

                refresh_month_warc_counts(conn, month)
                month_progress[month] = get_month_warc_counts(conn, month)
                print(
                    f"MONTH_DONE month={month} progress={month_progress[month]} "
                    f"elapsed_sec={perf_counter() - t_month_start:.2f}"
                )

        print(
            f"CCNEWS_DONE months={months} source_total_warcs={source_total_warcs} "
            f"selected_total_warcs={selected_total_warcs} skipped_done={skipped_done} "
            f"written_total={total_written} inserted_total={total_inserted} failed={failed}"
        )

        return {
            "months": months,
            "source_total_warcs": source_total_warcs,
            "selected_total_warcs": selected_total_warcs,
            "written_total": total_written,
            "inserted_total": total_inserted,
            "failed": failed,
            "month_progress": month_progress,
        }

    extract_and_load_month()