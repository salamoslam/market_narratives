
CREATE TABLE IF NOT EXISTS raw.ccnews_month_checkpoint (
    month TEXT PRIMARY KEY,
    total_warcs INT NOT NULL DEFAULT 0,
    done_warcs INT NOT NULL DEFAULT 0,
    failed_warcs INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_ccnews_month_checkpoint_updated_at
    ON raw.ccnews_month_checkpoint (updated_at DESC);