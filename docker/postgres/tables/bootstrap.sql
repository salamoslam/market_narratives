CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\i /docker-entrypoint-initdb.d/tables/news_articles/init.sql
\i /docker-entrypoint-initdb.d/tables/news_embeddings/init.sql
\i /docker-entrypoint-initdb.d/tables/news_articles/update.sql