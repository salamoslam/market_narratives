from pathlib import Path
import langid
import hashlib
from urllib.parse import urlsplit
import polars as pl
from src.config import get_settings
import psycopg
from typing import Sequence

def scan_tree(root: Path) -> pl.LazyFrame:
    parts = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if f.stat().st_size == 0:
            continue  # skip empty files

        s = f.suffix.lower()
        if s == ".jsonl":
            parts.append(pl.scan_ndjson(str(f)))
        elif s == ".parquet":
            parts.append(pl.scan_parquet(str(f)))
        elif s == ".csv":
            parts.append(pl.scan_csv(str(f), ignore_errors=True))

    return pl.concat(parts, how="diagonal_relaxed") if parts else pl.LazyFrame()


def domain_expr(url_col="url"):
    return (
        pl.col(url_col)
        .cast(pl.Utf8)
        .str.extract(r"^(?:https?://)?(?:www\.)?([^/]+)", 1)
        .fill_null("unknown")
        .alias("domain")
    )

def detect_lang(text: str) -> str | None:
    try:
        return langid.classify(text[:2000])[0]
    except Exception:
        return None


def hash_url(u: str) -> str:
    return hashlib.sha256(u.encode("utf-8")).hexdigest()

def hash_text500(t: str) -> str:
    x = t[:500].lower().strip()
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def insert_polars_to_postgres(
    df: pl.DataFrame,
    *,
    table_name: str,
    target_cols: Sequence[str],
    dsn: str | None = None,
    conflict_col: str = "article_id",
    batch_size: int = 5000,
    verbose: bool = True,
) -> dict[str, int]:

    if dsn is None:
        dsn = get_settings().postgres_dsn
    # keep only required cols in the exact order expected by SQL placeholders
    data = df.select(list(target_cols))
    n_total = data.height
    if n_total == 0:
        return {"rows_in_df": 0, "inserted_estimate": 0}
    insert_sql = f"""
    INSERT INTO {table_name} ({", ".join(target_cols)})
    VALUES ({", ".join(["%s"] * len(target_cols))})
    ON CONFLICT ({conflict_col}) DO NOTHING;
    """
    inserted_est = 0
    processed = 0
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            for chunk in data.iter_slices(n_rows=batch_size):
                rows = list(chunk.rows())
                cur.executemany(insert_sql, rows)
                inserted_est += max(cur.rowcount or 0, 0)
                processed += len(rows)
                if verbose:
                    print(f"processed={processed}/{n_total} ({processed / n_total:.1%})")
    return {"rows_in_df": n_total, "inserted_estimate": inserted_est}