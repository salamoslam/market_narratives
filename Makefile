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
	@.venv/bin/python -c 'import os, psycopg; sql=os.environ["SQL"]; conn=psycopg.connect(host=os.environ["POSTGRES_HOST"], port=os.environ["POSTGRES_PORT"], dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"], autocommit=True); cur=conn.execute(sql); rows=cur.fetchall() if cur.description else None; print("\n".join("\t".join("" if v is None else str(v) for v in row) for row in rows) if rows is not None else "ok")'

ingest:
	$(COMPOSE) exec jupyter python scripts/run_ingestion.py

notebook:
	@echo "Open: http://localhost:8888"

airflow:
	@echo "Open: http://localhost:8080"

debug-setup:
	./scripts/setup_debug_access.sh
