from __future__ import annotations

import numpy as np
import polars as pl
import psycopg
from sentence_transformers import SentenceTransformer
from pgvector.psycopg import register_vector

from src.db_utils.pg_utils import select_query

def _safe_text(x: str | None) -> str:
    return (x or "").strip()


def run_news_embeddings_transform_polars(
    *,
    model_name: str = "BAAI/bge-base-en-v1.5",   # 768-dim
    select_batch_size: int = 2000,
    encode_batch_size: int = 128,
    max_rows: int | None = None,
    normalize_embeddings: bool = True,
) -> dict[str, int]:
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()
    if dim != 768:
        raise ValueError(f"Model dim is {dim}, expected 768")

    processed = 0
    upserted = 0

    with psycopg.connect(dsn, autocommit=True) as conn:
        register_vector(conn)

        while True:
            if max_rows is not None and processed >= max_rows:
                break

            limit = select_batch_size if max_rows is None else min(select_batch_size, max_rows - processed)

            # pull batch -> polars dataframe
            query = """
                SELECT a.article_id, a.title, a.text
                FROM news_articles a
                LEFT JOIN news_embeddings e ON e.article_id = a.article_id
                WHERE e.article_id IS NULL
                ORDER BY a.datetime NULLS LAST, a.article_id
                LIMIT %s
            """
            
            batch_df = select_query(query, (limit,))
            if batch_df.height == 0:
                break

            titles = [_safe_text(x) for x in batch_df["title"].to_list()]
            texts = [_safe_text(x) for x in batch_df["text"].to_list()]

            title_vecs = model.encode(
                titles,
                batch_size=encode_batch_size,
                show_progress_bar=False,
                normalize_embeddings=normalize_embeddings,
            )
            text_vecs = model.encode(
                texts,
                batch_size=encode_batch_size,
                show_progress_bar=False,
                normalize_embeddings=normalize_embeddings,
            )

            emb_df = batch_df.select("article_id").with_columns(
                pl.Series("title_embedding", [np.asarray(v, dtype=np.float32).tolist() for v in title_vecs]),
                pl.Series("text_embedding", [np.asarray(v, dtype=np.float32).tolist() for v in text_vecs]),
            )

            payload = [
                (r["article_id"], np.asarray(r["title_embedding"], dtype=np.float32), np.asarray(r["text_embedding"], dtype=np.float32))
                for r in emb_df.iter_rows(named=True)
            ]

            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO news_embeddings (article_id, title_embedding, text_embedding, updated_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (article_id) DO UPDATE
                    SET title_embedding = EXCLUDED.title_embedding,
                        text_embedding = EXCLUDED.text_embedding,
                        updated_at = now()
                    """,
                    payload,
                )
                upserted += cur.rowcount or 0

            processed += emb_df.height
            print(f"processed={processed} upserted={upserted}")

    return {"processed": processed, "upserted": upserted, "embedding_dim": dim}