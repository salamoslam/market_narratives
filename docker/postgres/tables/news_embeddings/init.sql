CREATE TABLE IF NOT EXISTS news_embeddings (
    article_id TEXT PRIMARY KEY REFERENCES news_articles(article_id) ON DELETE CASCADE,
    text_embedding VECTOR(384),
    model_name TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
