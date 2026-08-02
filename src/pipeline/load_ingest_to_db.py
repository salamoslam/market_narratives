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

def domain_from_url(url: str | None) -> str:
    u = (url or "").strip()
    if not u:
        return "unknown"
    host = urlsplit(u).netloc or urlsplit(f"http://{u}").netloc
    host = host.lower().strip()
    if not host:
        return "unknown"
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"


_MULTI_PART_SUFFIXES = (
    ".co.uk",
    ".org.uk",
    ".ac.uk",
    ".gov.uk",
    ".com.au",
    ".co.nz",
    ".co.za",
)

_FEED_HOST_PREFIXES = ("rss.", "feeds.", "www.", "api.")


def registrable_domain(url_or_host: str) -> str:
    host = domain_from_url(url_or_host) if "://" in url_or_host else url_or_host.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    for suffix in _MULTI_PART_SUFFIXES:
        if host.endswith(suffix):
            base = host[: -len(suffix)]
            label = base.rsplit(".", 1)[-1]
            return f"{label}{suffix}"
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def _host_matches_domain(host: str, domain: str) -> bool:
    host = host.lower().strip()
    domain = domain.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host == domain or host.endswith("." + domain)


def domain_in_allowlist(host: str, allowed_domains: tuple[str, ...]) -> bool:
    host = domain_from_url(host) if "://" in host else host.lower().strip()
    reg = registrable_domain(host)
    for allowed in allowed_domains:
        allowed = allowed.lower().strip()
        if allowed.startswith("www."):
            allowed = allowed[4:]
        if _host_matches_domain(host, allowed) or reg == allowed or _host_matches_domain(reg, allowed):
            return True
    return False


def expected_article_domains(
    rss_url: str,
    publisher_domain_groups: tuple[tuple[str, ...], ...],
) -> set[str]:
    feed_host = domain_from_url(rss_url)
    domains = {feed_host, registrable_domain(feed_host)}
    for prefix in _FEED_HOST_PREFIXES:
        if feed_host.startswith(prefix):
            stripped = feed_host[len(prefix):]
            domains.add(stripped)
            domains.add(registrable_domain(stripped))
    expanded = set(domains)
    for domain in domains:
        for group in publisher_domain_groups:
            if any(domain == member or domain.endswith("." + member) or member in domain for member in group):
                expanded.update(group)
    return expanded


def url_allowed_for_rss_entry(
    article_url: str,
    rss_url: str,
    *,
    allowed_domains: tuple[str, ...],
    publisher_domain_groups: tuple[tuple[str, ...], ...],
    rss_proxy_feed_hosts: tuple[str, ...],
) -> bool:
    article_host = domain_from_url(article_url)
    if not article_host or article_host == "unknown":
        return False
    feed_host = domain_from_url(rss_url)
    if feed_host in rss_proxy_feed_hosts:
        return domain_in_allowlist(article_host, allowed_domains)
    expected = expected_article_domains(rss_url, publisher_domain_groups)
    article_reg = registrable_domain(article_host)
    for domain in expected:
        if _host_matches_domain(article_host, domain) or article_reg == domain:
            return True
    return False
    

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


def ingest_ccnews_jsonl_file(
    jsonl_path: str,
    *,
    dsn: str | None = None,
    source_type: str = "ccnews",
    verbose: bool = True,
) -> dict[str, int]:
    if dsn is None:
        dsn = get_settings().postgres_dsn

    lf = pl.scan_ndjson(jsonl_path)

    df = (
        lf.select(
            [
                pl.col("url").cast(pl.Utf8).alias("url"),
                pl.col("title").cast(pl.Utf8).alias("title"),
                pl.col("domain").cast(pl.Utf8).alias("domain_raw"),
                pl.col("date").cast(pl.Utf8).alias("datetime_str"),
                pl.col("author").cast(pl.Utf8).alias("author"),
                pl.col("lang").cast(pl.Utf8).alias("lang"),
                pl.col("text").cast(pl.Utf8).alias("text"),
            ]
        )
        .filter(
            pl.col("url").is_not_null()
            & pl.col("text").is_not_null()
            & (pl.col("url").str.len_chars() > 0)
            & (pl.col("text").str.len_chars() > 0)
        )
        .with_columns(
            [
                pl.lit(source_type).alias("source_type"),
                pl.col("url").map_elements(hash_url, return_dtype=pl.Utf8).alias("article_id"),
                pl.col("text").map_elements(hash_text500, return_dtype=pl.Utf8).alias("text_hash"),
                pl.when(pl.col("domain_raw").is_null() | (pl.col("domain_raw").str.len_chars() == 0))
                .then(pl.col("url").map_elements(domain_from_url, return_dtype=pl.Utf8))
                .otherwise(pl.col("domain_raw").str.to_lowercase())
                .alias("domain"),
                pl.col("datetime_str").str.strptime(pl.Datetime(time_zone="UTC"), strict=False).alias("datetime"),
            ]
        )
        .with_columns(pl.col("datetime").dt.date().alias("date"))
        .select(
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

    return insert_polars_to_postgres(
        df,
        table_name="raw.news_articles",
        target_cols=[
            "article_id", "text_hash", "source_type", "domain", "title",
            "url", "datetime", "date", "author", "lang", "text",
        ],
        dsn=dsn,
        conflict_col="article_id",
        batch_size=5000,
        verbose=verbose,
    )