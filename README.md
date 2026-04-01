# Global Narrative Monitor (Step 1)

Initial project structure for data ingestion and storage.

This step implements only:

- RSS ingestion
- GDELT ingestion
- Unified normalization
- Deduplication by hash
- PostgreSQL storage with `pgvector` enabled
- Airflow DAG scheduling every 30 minutes
- Jupyter notebooks for exploration

No ML, embeddings generation, clustering, or narrative detection is included yet.

## Repository structure

```text
market_narratives_engine/
├── dags/
│   └── ingest_news_dag.py
├── data/
│   ├── processed/
│   │   └── README.md
│   └── raw/
│       ├── gdelt/
│       │   └── .gitkeep
│       └── rss/
│           └── .gitkeep
├── docker/
│   ├── airflow/
│   │   └── Dockerfile
│   ├── jupyter/
│   │   └── Dockerfile
│   └── postgres/
│       └── init.sql
├── notebooks/
│   ├── 01_explore_gdelt.ipynb
│   ├── 02_explore_rss.ipynb
│   └── 03_unified_schema.ipynb
├── Makefile
├── scripts/
│   ├── init_db.py
│   └── run_ingestion.py
├── src/
│   ├── collectors/
│   │   ├── gdelt_collector.py
│   │   └── rss_collector.py
│   ├── pipeline/
│   │   └── ingest_news.py
│   ├── storage/
│   │   ├── database.py
│   │   └── models.py
│   └── config.py
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

## Data model

Table: `news_articles`

- `id` UUID primary key
- `source` text
- `title` text
- `url` text
- `published_at` timestamptz nullable
- `collected_at` timestamptz
- `origin` text (`rss` or `gdelt`)
- `language` text nullable
- `hash` text unique for deduplication
- `embedding` vector(1536) nullable for future use

## Unified article schema

`NewsArticle` in `src/storage/models.py` has:

- `source`
- `title`
- `url`
- `published_at`
- `origin`
- `language`

Both collectors output this schema.

## Quick start

1. Create environment file:

```bash
cp .env.example .env
```

Install project package locally once:

```bash
python -m pip install -e .
```

2. Start services:

```bash
make up
```

First run builds images and installs dependencies into images.
Next restarts reuse those images and start quickly without reinstalling.

3. Initialize database schema:

```bash
make init-db
```

4. Run one ingestion cycle manually:

```bash
make ingest
```

## Make targets

- `make up` start all containers
- `make build` build service images
- `make down` stop and remove containers
- `make restart` restart full stack
- `make rebuild` rebuild images and restart stack
- `make ps` show container status
- `make logs` stream container logs
- `make init-db` create extensions and table
- `make ingest` run one ingestion cycle
- `make notebook` print Jupyter URL
- `make airflow` print Airflow URL

## Airflow

- URL: `http://localhost:8080`
- DAG: `ingest_news`
- Schedule: every 30 minutes (`*/30 * * * *`)

The DAG tasks are:

- `collect_rss`
- `collect_gdelt`
- `normalize_data`
- `store_articles`

## Jupyter

- URL: `http://localhost:8888`
- Token is disabled in this local setup
- Notebooks:
  - `notebooks/01_explore_gdelt.ipynb`
  - `notebooks/02_explore_rss.ipynb`
  - `notebooks/03_unified_schema.ipynb`

## GDELT notes

The current GDELT collector downloads the latest export file from `gdeltv2`.
It extracts URL and timestamp directly from export rows.
Language is best-effort from theme tokens when present.

## Future steps

Later steps can add:

- embeddings computation
- vector similarity search
- clustering
- narrative detection
- market impact analysis
