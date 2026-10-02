SET maintenance_work_mem = '32MB';
SET max_parallel_maintenance_workers = 0;

DROP TABLE IF EXISTS raw.news_article_duplicates_to_delete;

CREATE UNLOGGED TABLE raw.news_article_duplicates_to_delete (
    article_id TEXT NOT NULL
);

INSERT INTO raw.news_article_duplicates_to_delete (article_id)
WITH duplicate_lead_hashes AS (
    SELECT text_hash
    FROM raw.news_articles
    GROUP BY text_hash
    HAVING count(*) > 1
),
ranked_articles AS (
    SELECT
        article.article_id,
        row_number() OVER (
            PARTITION BY digest(convert_to(article.text, 'UTF8'), 'sha256')
            ORDER BY article.datetime NULLS LAST, article.article_id
        ) AS duplicate_rank
    FROM raw.news_articles AS article
    JOIN duplicate_lead_hashes USING (text_hash)
)
SELECT article_id
FROM ranked_articles
WHERE duplicate_rank > 1;

ALTER TABLE raw.news_article_duplicates_to_delete
ADD PRIMARY KEY (article_id);

SELECT count(*) AS rows_to_delete
FROM raw.news_article_duplicates_to_delete;

SELECT format(
    'DELETE FROM raw.news_articles AS article USING raw.news_article_duplicates_to_delete AS duplicate WHERE article.article_id = duplicate.article_id AND duplicate.article_id >= %L AND duplicate.article_id < %L',
    lpad(to_hex(batch_number), 2, '0'),
    CASE
        WHEN batch_number = 255 THEN 'g'
        ELSE lpad(to_hex(batch_number + 1), 2, '0')
    END
)
FROM generate_series(0, 255) AS batch_number
\gexec

DROP TABLE raw.news_article_duplicates_to_delete;

VACUUM (ANALYZE, PARALLEL 0) raw.news_articles;
VACUUM (ANALYZE, PARALLEL 0) raw.news_embeddings;
