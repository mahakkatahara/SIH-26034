"""
Alembic environment configuration for async SQLAlchemy
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Load app models and config
from app.core.config import settings
from app.database.session import Base

# Import all models so Alembic can detect them
import app.models  # noqa: F401

config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

import os

# Resolve database URL: programmatic override (if explicitly changed) > env var > settings > default
configured_url = config.get_main_option("sqlalchemy.url")
default_ini_url = "postgresql+asyncpg://lmis_user:changeme@localhost:5432/legal_metrology_db"

if configured_url and configured_url != default_ini_url:
    target_url = configured_url
elif os.environ.get("DATABASE_URL"):
    target_url = os.environ["DATABASE_URL"]
elif settings and getattr(settings, "DATABASE_URL", None):
    target_url = settings.DATABASE_URL
else:
    target_url = configured_url

if target_url:
    config.set_main_option("sqlalchemy.url", target_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, run_async_migrations())
            future.result()
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
