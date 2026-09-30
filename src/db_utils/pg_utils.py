import polars as pl
import psycopg
from src.config import get_settings
from pgvector.psycopg import register_vector


def select_query(
    sql: str,
    params: tuple | list | None = None,
    dsn: str | None = None,
    vector: bool = True,
) -> pl.DataFrame:
    """
    Execute a SELECT query and return the results as a Polars DataFrame.

    Args:
        sql (str): The SQL query to execute.
        params (tuple | list | None, optional): The parameters to pass to the query.
        dsn (str | None, optional): The DSN to use for the connection.
        vector (bool, optional): Whether to register the vector extension.

    Returns:
        pl.DataFrame: The results of the query as a Polars DataFrame.
    """
    if dsn is None:
        dsn = get_settings().postgres_dsn
    with psycopg.connect(dsn) as conn:
        if vector:
            register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            cols = [d.name for d in cur.description] if cur.description else []
    return pl.DataFrame(rows, schema=cols, orient="row") if cols else pl.DataFrame()


def execute_query(
    sql: str,
    params: tuple | list | None = None,
    dsn: str | None = None,
    autocommit: bool = False,
) -> None:
    """
    Execute a SQL query and return the results as a Polars DataFrame.

    Args:
        sql (str): The SQL query to execute.
        params (tuple | list | None, optional): The parameters to pass to the query.
        dsn (str | None, optional): The DSN to use for the connection.
        autocommit (bool, optional): Whether to commit the transaction.

    Returns:
        None
    """
    if dsn is None:
        dsn = get_settings().postgres_dsn
    with psycopg.connect(dsn, autocommit=autocommit) as conn:

        with conn.cursor() as cur:
            cur.execute(sql, params or ())
