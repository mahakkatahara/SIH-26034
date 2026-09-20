#!/bin/sh
set -e

echo "[entrypoint] Applying database migrations (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] Seeding initial database data (python -m app.scripts.seed)..."
python -m app.scripts.seed

echo "[entrypoint] Starting application server: $@"
exec "$@"
