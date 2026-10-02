SET maintenance_work_mem = '32MB';
SET max_parallel_maintenance_workers = 0;

DROP INDEX IF EXISTS raw.idx_articles_text_hash;
DROP INDEX IF EXISTS raw.idx_raw_articles_text_hash;

SELECT format(
    'UPDATE raw.news_articles SET text_hash = encode(digest(convert_to(text, ''UTF8''), ''sha256''), ''hex'') WHERE article_id >= %L AND article_id < %L',
    lpad(to_hex(batch_number), 2, '0'),
    CASE
        WHEN batch_number = 255 THEN 'g'
        ELSE lpad(to_hex(batch_number + 1), 2, '0')
    END
)
FROM generate_series(0, 255) AS batch_number
\gexec

VACUUM (ANALYZE, PARALLEL 0) raw.news_articles;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'raw.news_articles'::regclass
          AND conname = 'news_articles_text_hash_key'
    ) THEN
        ALTER TABLE raw.news_articles
        ADD CONSTRAINT news_articles_text_hash_key UNIQUE (text_hash);
    END IF;
END
$$;
