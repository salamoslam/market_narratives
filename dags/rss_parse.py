from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

import polars as pl
from airflow import DAG
from airflow.decorators import task

from src.collectors.rss_utils import run_rss_cycle
from src.config import get_settings
from src.pipeline.load_ingest_to_db import insert_polars_to_postgres, scan_tree
import asyncio

with DAG(
    dag_id="rss_parse_and_load",
    start_date=datetime(2026, 1, 1),
    schedule="0 */3 * * *",
    catchup=False,
    tags=["rss", "ingestion"],
    max_active_runs=1,   
    max_active_tasks=1,  
) as dag:
    @task
    def parse_rss_to_disk() -> dict[str, int]:
        settings = get_settings()
        out_root = Path("/opt/airflow/project/data/raw/rss")
        stats, _ = asyncio.run(run_rss_cycle(
            settings.rss_feeds,
            out_root=str(out_root),
        ))
        return stats

    @task
    def load_rss_to_db() -> dict[str, int]:
        settings = get_settings()
        rss_root = Path("/opt/airflow/project/data/raw/rss")

        jsonl_files = [p for p in rss_root.rglob("*.jsonl") if p.is_file()]
        if not jsonl_files:
            return {"rows_in_df": 0, "inserted_estimate": 0}

        rss_lf = scan_tree(rss_root)

        cols = set(rss_lf.collect_schema().names())
        datetime_col = (
                pl.col("datetime").cast(pl.Utf8)
                if "datetime" in cols
                else pl.lit(None, dtype=pl.Utf8)
        )
        date_col = (
            pl.col("date").cast(pl.Utf8)
            if "date" in cols
            else pl.lit(None, dtype=pl.Utf8)
        )

        rss_lf = rss_lf.select([
            # [
                pl.lit("rss").alias("source_type"),
                pl.col("domain").cast(pl.Utf8).str.to_lowercase().alias("domain"),
                pl.col("title").cast(pl.Utf8).alias("title"),
                pl.col("url").cast(pl.Utf8).alias("url"),
                pl.coalesce([datetime_col, date_col + pl.lit("T00:00:00+00:00")]).alias("datetime_str"),
                date_col.alias("date_str"),
                pl.col("author").cast(pl.Utf8).alias("author"),
                pl.col("lang").cast(pl.Utf8).alias("lang"),
                pl.col("text").cast(pl.Utf8).alias("text"),
            ]
        ).with_columns([
            pl.col("datetime_str").str.strptime(
                pl.Datetime(time_zone="UTC"),
                format="%Y-%m-%dT%H:%M:%S%z",
                strict=False,
            ).alias("datetime"),
            pl.col("date_str").str.strptime(pl.Date, strict=False).alias("date"),
        ]
        ).filter(
            pl.col("url").is_not_null()
            & pl.col("text").is_not_null()
            & (pl.col("url").str.len_chars() > 0)
            & (pl.col("text").str.len_chars() > 0)
        )

        rss_lf = rss_lf.with_columns(
            [
                pl.col("url")
                .map_elements(
                    lambda u: sha256(u.encode("utf-8")).hexdigest(),
                    return_dtype=pl.Utf8,
                )
                .alias("article_id"),
                pl.col("text")
                .map_elements(
                    lambda t: sha256(t[:500].lower().strip().encode("utf-8")).hexdigest(),
                    return_dtype=pl.Utf8,
                )
                .alias("text_hash"),
            ]
        )

        df = (
            rss_lf.select(
                [
                    "article_id",
                    "text_hash",
                    "source_type",
                    "domain",
                    "title",
                    "url",
                    "datetime",
                    "date",
                    "author",
                    "lang",
                    "text",
                ]
            )
            .unique(subset=["article_id"], keep="first")
            .collect(streaming=True)
        )

        stats = insert_polars_to_postgres(
            df,
            table_name="news_articles",
            target_cols=[
                "article_id",
                "text_hash",
                "source_type",
                "domain",
                "title",
                "url",
                "datetime",
                "date",
                "author",
                "lang",
                "text",
            ],
            dsn=settings.postgres_dsn,
            conflict_col="article_id",
            batch_size=5000,
            verbose=True,
        )
        return stats

    @task
    def cleanup_old_rss_files(retention_days: int = 30) -> int:
        rss_root = Path("/opt/airflow/project/data/raw/rss")
        if not rss_root.exists():
            return 0

        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        deleted = 0
        for path in rss_root.rglob("*.jsonl"):
            mtime = datetime.utcfromtimestamp(path.stat().st_mtime)
            if mtime < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
        return deleted

    parse_task = parse_rss_to_disk()
    load_task = load_rss_to_db()
    cleanup_task = cleanup_old_rss_files(retention_days=30)

    parse_task >> load_task >> cleanup_task
