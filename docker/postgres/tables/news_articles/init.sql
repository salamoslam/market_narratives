CREATE TABLE IF NOT EXISTS raw.news_articles (
    article_id TEXT PRIMARY KEY,
    text_hash TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_warc TEXT,
    domain TEXT,
    title TEXT,
    url TEXT NOT NULL,
    datetime TIMESTAMPTZ,
    date DATE,
    author TEXT,
    lang TEXT,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_articles_source_type
    ON raw.news_articles (source_type);
CREATE INDEX IF NOT EXISTS idx_raw_articles_date
    ON raw.news_articles (date);
CREATE INDEX IF NOT EXISTS idx_raw_articles_datetime
    ON raw.news_articles (datetime);
CREATE INDEX IF NOT EXISTS idx_raw_articles_text_hash
    ON raw.news_articles (text_hash);
CREATE INDEX IF NOT EXISTS idx_raw_articles_domain
    ON raw.news_articles (domain);
CREATE INDEX IF NOT EXISTS idx_raw_articles_source_warc
    ON raw.news_articles (source_warc);