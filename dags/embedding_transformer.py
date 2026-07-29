from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable

from src.pipeline.news_embedding import run_embeddings_transform


NUM_SHARDS = int(Variable.get("news_embeddings_num_shards", default_var="2"))
SELECT_BATCH_SIZE = int(Variable.get("news_embeddings_select_batch_size", default_var="500"))
ENCODE_BATCH_SIZE = int(Variable.get("news_embeddings_encode_batch_size", default_var="32"))


with DAG(
    dag_id="news_embeddings_update",
    start_date=datetime(2026, 5, 17),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    max_active_tasks=NUM_SHARDS,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["embeddings", "news"],
) as dag:
    @task
    def update_news_embeddings(shard_id: int, num_shards: int = NUM_SHARDS) -> dict[str, int]:
        return run_embeddings_transform(
            max_rows=None,
            select_batch_size=SELECT_BATCH_SIZE,
            encode_batch_size=ENCODE_BATCH_SIZE,
            normalize_embeddings=True,
            device="cpu",
            shard_id=shard_id,
            num_shards=num_shards,
        )

    update_news_embeddings.partial(num_shards=NUM_SHARDS).expand(
        shard_id=list(range(NUM_SHARDS))
    )
