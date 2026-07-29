from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable

from src.pipeline.news_embedding import run_embeddings_transform


MAX_SHARDS = 8


def _embedding_var(name: str, default: str) -> int:
    return int(Variable.get(name, default_var=default))


with DAG(
    dag_id="news_embeddings_update",
    start_date=datetime(2026, 5, 17),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    max_active_tasks=MAX_SHARDS,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["embeddings", "news"],
) as dag:
    @task
    def get_shard_ids() -> list[int]:
        num_shards = _embedding_var("news_embeddings_num_shards", "2")
        if num_shards < 1:
            raise ValueError(f"news_embeddings_num_shards must be >= 1, got {num_shards}")
        if num_shards > MAX_SHARDS:
            raise ValueError(f"news_embeddings_num_shards must be <= {MAX_SHARDS}, got {num_shards}")
        return list(range(num_shards))

    @task
    def update_news_embeddings(shard_id: int) -> dict[str, int]:
        num_shards = _embedding_var("news_embeddings_num_shards", "2")
        return run_embeddings_transform(
            max_rows=None,
            select_batch_size=_embedding_var("news_embeddings_select_batch_size", "500"),
            encode_batch_size=_embedding_var("news_embeddings_encode_batch_size", "32"),
            normalize_embeddings=True,
            device="cpu",
            shard_id=shard_id,
            num_shards=num_shards,
        )

    update_news_embeddings.expand(shard_id=get_shard_ids())
