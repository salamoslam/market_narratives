from __future__ import annotations

import os
import time
from pathlib import Path

import polars as pl
from openai import OpenAI
from tqdm import tqdm

from src.labeling.prompt import SYSTEM_PROMPT, article_user_prompt, parse_label_response


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def label_article(
    client: OpenAI,
    *,
    model: str,
    title: str,
    text: str,
    domain: str | None = None,
    max_text_chars: int = 2000,
) -> list[str]:
    """
    Label an article using the OpenAI API.

    Args:
        client (OpenAI): The OpenAI client.
        model (str): The model to use for labeling.
        title (str): The title of the article.
        text (str): The article text.
        domain (str | None, optional): The source domain of the article, if available.
        max_text_chars (int, optional): The maximum number of characters from the article text to include in the prompt.

    Returns:
        list[str]: A list of labels extracted from the response.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": article_user_prompt(
                    title=title,
                    text=text,
                    domain=domain,
                    max_text_chars=max_text_chars,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = response.choices[0].message.content or "{}"
    return parse_label_response(raw)


def label_articles(
    df: pl.DataFrame,
    output_path: str | Path,
    *,
    model: str | None = None,
    sleep_s: float = 0.05,
    max_text_chars: int = 2000,
) -> pl.DataFrame:
    """
    Label a dataframe of articles using the OpenAI API.

    Args:
        df (pl.DataFrame): The dataframe of articles to label.
        output_path (str | Path): The path to the output parquet file.
        model (str | None, optional): The model to use for labeling.
        sleep_s (float, optional): The sleep time between requests.
        max_text_chars (int, optional): The maximum number of characters from the article text to include in the prompt.

    Returns:
        pl.DataFrame: A dataframe of labeled articles.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = get_openai_client()

    done_ids: set[str] = set()
    rows: list[dict] = []
    if output_path.exists():
        existing = pl.read_parquet(output_path)
        done_ids = set(existing["article_id"].to_list())
        rows = existing.to_dicts()

    pending = df.filter(~pl.col("article_id").is_in(list(done_ids)))
    for row in tqdm(pending.iter_rows(named=True), total=pending.height):
        labels = label_article(
            client,
            model=model,
            title=row.get("title") or "",
            text=row.get("text") or "",
            domain=row.get("domain"),
            max_text_chars=max_text_chars,
        )
        rows.append(
            {
                "article_id": row["article_id"],
                "title": row.get("title"),
                "domain": row.get("domain"),
                "datetime": row.get("datetime"),
                "labels": labels,
                "model": model,
            }
        )
        if sleep_s:
            time.sleep(sleep_s)

        if len(rows) % 25 == 0:
            pl.DataFrame(rows).write_parquet(output_path)

    result = pl.DataFrame(rows)
    result.write_parquet(output_path)
    return result
