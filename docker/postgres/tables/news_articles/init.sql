CREATE TABLE IF NOT EXISTS news_articles (
    article_id TEXT PRIMARY KEY,
    text_hash TEXT NOT NULL,
    source_type TEXT NOT NULL,
    domain TEXT,
    title TEXT,
    url TEXT NOT NULL,
    datetime TIMESTAMPTZ,
    date DATE,
    author TEXT,
    lang TEXT,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_source_type ON news_articles (source_type);
CREATE INDEX IF NOT EXISTS idx_articles_date ON news_articles (date);
CREATE INDEX IF NOT EXISTS idx_articles_text_hash ON news_articles (text_hash);