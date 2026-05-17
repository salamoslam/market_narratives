UPDATE news_articles
SET domain = regexp_replace(domain, '^www\.', '')
WHERE domain LIKE 'www.%'
  AND date >= DATE '2026-03-01';