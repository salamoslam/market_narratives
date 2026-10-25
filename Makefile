-include .env
export  

COMPOSE := docker compose
POSTGRES_SERVICE := postgres

.PHONY: install-local build up down restart rebuild init-db db-run db-query db-query-prod ingest logs ps notebook airflow debug-setup

install-local:
	python -m pip install -e .

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart: down up

rebuild: down build up

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

init-db:
	$(COMPOSE) exec jupyter python scripts/init_db.py

db-run:
	$(COMPOSE) exec -T -e PGPASSWORD="$(POSTGRES_PASSWORD)" $(POSTGRES_SERVICE) \
		psql -v ON_ERROR_STOP=1 \
		-U "$(POSTGRES_USER)" \
		-d "$(POSTGRES_DB)" \
		-f /docker-entrypoint-initdb.d/$(SQL)

db-query:
	$(COMPOSE) exec -T -e PGPASSWORD="$(POSTGRES_PASSWORD)" $(POSTGRES_SERVICE) \
		psql -v ON_ERROR_STOP=1 \
		-U "$(POSTGRES_USER)" \
		-d "$(POSTGRES_DB)" \
		-c "$(SQL)"

db-query-prod:
	@test -n "$(SQL)" || { echo 'usage: make db-query-prod SQL="select 1"'; exit 1; }
	@.venv/bin/python -c 'import os, pathlib, psycopg; env={}; \
	[env.update({k.strip(): v.strip().strip(chr(34))}) for line in pathlib.Path(".env.readonly").read_text().splitlines() if (s:=line.strip()) and not s.startswith("#") and "=" in s for k, v in [s.split("=", 1)]]; \
	conn=psycopg.connect(host=env["POSTGRES_HOST"], port=env["POSTGRES_PORT"], dbname=env["POSTGRES_DB"], user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"], autocommit=True); \
	conn.execute("set default_transaction_read_only to on"); \
	cur=conn.execute(os.environ["SQL"]); \
	rows=cur.fetchall() if cur.description else None; \
	print("ok" if rows is None else "\n".join(chr(9).join("" if v is None else str(v) for v in row) for row in rows))'

ingest:
	$(COMPOSE) exec jupyter python scripts/run_ingestion.py

notebook:
	@echo "Open: http://localhost:8888"

airflow:
	@echo "Open: http://localhost:8080"

debug-setup:
	./scripts/setup_debug_access.sh
