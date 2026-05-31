from __future__ import annotations

import numpy as np
import polars as pl
import psycopg
from pgvector.psycopg import register_vector
from src.config import get_settings

def _safe_text(x: str | None) -> str:
    return (x or "").strip()


def run_embeddings_transform(
    *,
    model_name: str = "intfloat/multilingual-e5-small",
    select_batch_size: int = 2000,
    encode_batch_size: int = 128,
    max_rows: int | None = None,
    normalize_embeddings: bool = True,
    device: str = "cpu"
) -> dict[str, int]:

    from sentence_transformers import SentenceTransformer

    dsn = get_settings().postgres_dsn

    print(f"[EMB_START] model={model_name} select_batch_size={select_batch_size} encode_batch_size={encode_batch_size} max_rows={max_rows} normalize={normalize_embeddings}")

    model = SentenceTransformer(model_name, device=device)
    dim = model.get_embedding_dimension()
    print(f"[EMB_MODEL] embedding_dim={dim}")
    if dim != 384:
        raise ValueError(f"Model dim is {dim}, expected 384")

    processed = 0
    upserted = 0
    batch_idx = 0

    with psycopg.connect(dsn, autocommit=True) as conn:
        register_vector(conn)

        print("[EMB_DB] connected")

        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS tmp_news_to_embed")
            cur.execute(
                """
                CREATE TEMP TABLE tmp_news_to_embed AS
                SELECT
                    a.article_id,
                    CASE
                        WHEN %s = 'intfloat/multilingual-e5-small'
                            THEN 'passage: ' || a.title || ' ' || a.text
                        ELSE a.title || ' ' || a.text
                    END AS text,
                    a.datetime
                FROM raw.news_articles a
                LEFT JOIN raw.news_embeddings e ON e.article_id = a.article_id
                WHERE e.article_id IS NULL
                """,
                (model_name,),
            )
            cur.execute(
                "CREATE INDEX tmp_news_to_embed_dt_id_idx ON tmp_news_to_embed (datetime DESC NULLS LAST, article_id)"
            )
        
        while True:
            if max_rows is not None and processed >= max_rows:
                print(f"[EMB_STOP] reached max_rows={max_rows}")
                break

            limit = select_batch_size if max_rows is None else min(select_batch_size, max_rows - processed)
            batch_idx += 1
            print(f"[EMB_BATCH_START] batch={batch_idx} limit={limit} processed_so_far={processed}")

            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT article_id, text
                    FROM tmp_news_to_embed
                    ORDER BY datetime DESC NULLS LAST, article_id
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
            if not rows:
                print(f"[EMB_BATCH_EMPTY] batch={batch_idx} no rows left")
                break

            batch_df = pl.DataFrame(rows, schema=["article_id", "text"], orient="row")

            texts = [_safe_text(x) for x in batch_df["text"].to_list()]

            non_empty_texts = sum(1 for x in texts if x)
            print(f"[EMB_BATCH_ROWS] batch={batch_idx} rows={batch_df.height} non_empty_texts={non_empty_texts}")


            text_vecs = model.encode(
                texts,
                batch_size=encode_batch_size,
                show_progress_bar=True,
                normalize_embeddings=normalize_embeddings,
            )

            emb_df = batch_df.select("article_id").with_columns(
                pl.Series("text_embedding", [np.asarray(v, dtype=np.float32).tolist() for v in text_vecs]),
            )

            payload = [
                (r["article_id"], np.asarray(r["text_embedding"], dtype=np.float32), model_name)
                for r in emb_df.iter_rows(named=True)
            ]

            sample_id = payload[0][0] if payload else None
            print(f"[EMB_BATCH_PAYLOAD] batch={batch_idx} payload_rows={len(payload)} sample_article_id={sample_id}")
            
            ids_to_delete = [r[0] for r in rows]

            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO raw.news_embeddings (article_id, text_embedding, model_name, updated_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (article_id) DO UPDATE
                    SET model_name = EXCLUDED.model_name,
                        text_embedding = EXCLUDED.text_embedding,
                        updated_at = now()
                    """,
                    payload,
                )
                delta = cur.rowcount or 0
                upserted += delta

                cur.execute(
                    "DELETE FROM tmp_news_to_embed WHERE article_id = ANY(%s)",
                    (ids_to_delete,),
                )

            processed += emb_df.height
            print(f"[EMB_BATCH_DONE] batch={batch_idx} batch_rows={emb_df.height} batch_upserted={delta} total_processed={processed} total_upserted={upserted}")

    print(f"[EMB_DONE] processed={processed} upserted={upserted} embedding_dim={dim}")

    return {"processed": processed, "upserted": upserted, "embedding_dim": dim}
