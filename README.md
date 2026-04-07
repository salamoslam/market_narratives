# Global Narrative Monitor

Clean and interpretable data ingestion project for global news collection and storage.

Current scope:

- Historical ingestion from Common Crawl CC-NEWS (manual/domain-filtered extraction)
- Incremental ingestion from RSS feeds
- Unified schema construction in notebooks
- Deduplication by URL hash and short-text hash
- PostgreSQL storage in Docker
- Airflow + Jupyter local stack for orchestration and research

No embeddings, clustering, or narrative modeling are included yet.

---

## Repository structure

```text
market_narratives_engine/
├── dags/
│   └── ingest_news_dag.py
├── data/
│   ├── raw/
│   │   ├── ccnews/
│   │   ├── rss/
│   │   └── rjac__all-the-news-2-1-Component-one/
│   └── processed/
├── docker/
│   ├── airflow/
│   │   └── Dockerfile
│   ├── jupyter/
│   │   └── Dockerfile
│   └── postgres/
│       ├── init.sql
│       └── tables/
│           └── news_articles/
│               └── init.sql
├── notebooks/
│   ├── 01_ccnews_extraction.ipynb
│   ├── 02_ccnews_check_domains.ipynb
│   ├── 03_collect_bulk_news_dfs.ipynb
│   ├── 04_explore_rss.ipynb
│   └── 05_unified_schema.ipynb
├── scripts/
│   ├── init_db.py
│   └── run_ingestion.py
├── src/
│   ├── collectors/
│   │   ├── ccnews_extractor.py
│   │   └── rss_collector.py
│   ├── pipeline/
│   │   ├── ingest_news.py
│   │   └── load_ingest_to_db.py
│   ├── storage/
│   │   ├── database.py
│   │   └── models.py
│   ├── config.py
│   └── config.json
├── docker-compose.yml
├── Makefile
├── .env.example
├── requirements.txt
└── README.md
```

