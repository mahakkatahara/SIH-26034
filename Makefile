.PHONY: help up down build logs db-shell backend-shell migrate seed dump-schema test-backend test-frontend lint

# Default target
help:
	@echo "SIH-26034 Legal Metrology Inspection System"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  up              Start all services with Docker Compose"
	@echo "  down            Stop all services"
	@echo "  build           Rebuild all Docker images"
	@echo "  logs            Tail logs for all services"
	@echo "  db-shell        Open PostgreSQL shell"
	@echo "  backend-shell   Open bash shell in backend container"
	@echo "  migrate         Run Alembic database migrations"
	@echo "  seed            Seed the database with initial data"
	@echo "  dump-schema     Dump canonical schema artifact from migrated DB"
	@echo "  test-backend    Run backend tests"
	@echo "  test-frontend   Run frontend tests"
	@echo "  lint            Run linters on all code"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

db-shell:
	docker compose exec db psql -U $${POSTGRES_USER:-lmis_user} -d $${POSTGRES_DB:-legal_metrology_db}

backend-shell:
	docker compose exec backend bash

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.scripts.seed

dump-schema:
	docker compose exec -T db pg_dump -U $${POSTGRES_USER:-lmis_user} -d $${POSTGRES_DB:-legal_metrology_db} --schema-only --no-owner --no-privileges > database/schema.sql

test-backend:
	cd backend && python -m pytest tests/ -v

test-frontend:
	cd frontend && npm test

lint:
	cd backend && python -m flake8 app/ && python -m mypy app/
	cd frontend && npm run lint
