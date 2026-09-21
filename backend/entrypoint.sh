#!/bin/sh
set -e

echo "[entrypoint] Applying database migrations (alembic upgrade head)..."
alembic upgrade head

if [ "$SEED_ON_START" = "true" ] || [ "$SEED_ON_START" = "1" ]; then
    echo "[entrypoint] SEED_ON_START is set; seeding initial database data (python -m app.scripts.seed)..."
    python -m app.scripts.seed
else
    echo "[entrypoint] SEED_ON_START is not set; skipping database seeding."
fi

echo "[entrypoint] Starting application server: $@"
exec "$@"
