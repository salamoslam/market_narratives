from __future__ import annotations

import json

THEME_LABELS: tuple[str, ...] = (
    "politics",
    "economics",
    "technology",
    "conflicts",
    "energy",
    "sanctions",
    "markets",
    "regulation",
    "corporate",
    "crime",
    "disasters",
    "health",
    "science",
    "sports",
    "entertainment",
    "lifestyle",
    "other",
)

SYSTEM_PROMPT = f"""You label news articles with a multi-label taxonomy for market and geopolitical analysis.

Allowed labels (use exact strings only):
{json.dumps(list(THEME_LABELS))}

Rules:
- Pick every label that clearly applies. Most articles have 1-3 labels.
- Use "other" only when nothing else fits.
- Do not invent labels outside the list.
- Ignore ads, boilerplate, and navigation text.
- politics: government, elections, diplomacy, geopolitics, policy
- economics: macro, trade, inflation, GDP, fiscal policy
- markets: stocks, bonds, FX, commodities, investors, earnings market reaction
- corporate: company news, M&A, management, products when not mainly a market move
- conflicts: war, military operations, armed conflict
- energy: oil, gas, power, OPEC, pipelines, renewables industry
- sanctions: export controls, trade restrictions, asset freezes
- regulation: laws, regulators, compliance, antitrust
- crime/disasters/sports/entertainment/lifestyle/health/science: use plain meaning
- Prefer market-relevant labels when the story affects policy, markets, or geopolitical risk.

Respond with JSON only:
{{"labels": ["politics", "economics"]}}
"""


def article_user_prompt(
    *,
    title: str,
    text: str,
    domain: str | None = None,
    max_text_chars: int = 2000,
) -> str:
    """
    Generate a user prompt string for article labeling.

    Args:
        title (str): The title of the article.
        text (str): The article text.
        domain (str | None, optional): The source domain of the article, if available.
        max_text_chars (int, optional): The maximum number of characters from the article text to include in the prompt.

    Returns:
        str: A formatted prompt string with title, optional domain, and a truncated article body.
    """
    body = (text or "").strip()
    if len(body) > max_text_chars:
        body = body[:max_text_chars] + "…"
    parts = [f"title: {(title or '').strip()}"]
    if domain:
        parts.append(f"domain: {domain.strip()}")
    parts.append(f"text: {body}")
    return "\n".join(parts)


def parse_label_response(raw: str) -> list[str]:
    """
    Parse the JSON response from the labeling model and return a list of labels.

    Args:
        raw (str): The raw JSON response from the labeling model.

    Returns:
        list[str]: A list of labels extracted from the response.
    """
    data = json.loads(raw)
    labels = data.get("labels", [])
    if not isinstance(labels, list):
        raise ValueError("labels must be a list")
    allowed = set(THEME_LABELS)
    cleaned = []
    for label in labels:
        if not isinstance(label, str):
            continue
        label = label.strip().lower()
        if label in allowed and label not in cleaned:
            cleaned.append(label)
    if not cleaned:
        cleaned = ["other"]
    return cleaned
