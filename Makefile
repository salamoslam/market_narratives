COMPOSE := docker compose

.PHONY: install-local build up down restart rebuild init-db ingest logs ps notebook airflow

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

ingest:
	$(COMPOSE) exec jupyter python scripts/run_ingestion.py

notebook:
	@echo "Open: http://localhost:8888"

airflow:
	@echo "Open: http://localhost:8080"
