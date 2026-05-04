CREATE TABLE IF NOT EXISTS news_embeddings (
    article_id TEXT PRIMARY KEY REFERENCES news_articles(article_id) ON DELETE CASCADE,
    title_embedding VECTOR(768),
    text_embedding VECTOR(768),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
