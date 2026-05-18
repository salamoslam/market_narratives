from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task

from src.pipeline.news_embedding import run_embeddings_transform


with DAG(
    dag_id="news_embeddings_update",
    start_date=datetime(2026, 5, 17),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["embeddings", "news"],
) as dag:
    @task
    def update_news_embeddings() -> dict[str, int]:
        return run_embeddings_transform(
            max_rows=None,
            select_batch_size=2000,
            encode_batch_size=128,
            normalize_embeddings=True,
            device="cpu",
        )

    update_news_embeddings()