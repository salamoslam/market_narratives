import polars as pl
import psycopg
from src.config import get_settings


def select_query(sql: str, params: tuple | list | None = None, dsn: str | None = None) -> pl.DataFrame:
    if dsn is None:
        dsn = get_settings().postgres_dsn
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            cols = [d.name for d in cur.description] if cur.description else []
    return pl.DataFrame(rows, schema=cols, orient="row") if cols else pl.DataFrame()
