CREATE TABLE IF NOT EXISTS raw.ccnews_warc_checkpoint (
    warc_path TEXT PRIMARY KEY,
    month TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'done', 'failed')),
    rows_written INT NOT NULL DEFAULT 0,
    rows_inserted INT NOT NULL DEFAULT 0,
    error_text TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_ccnews_warc_checkpoint_month_status
    ON raw.ccnews_warc_checkpoint (month, status);