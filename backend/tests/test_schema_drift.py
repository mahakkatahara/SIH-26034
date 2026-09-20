"""
Tests for Schema Drift and Migration Integrity.
Prevents discrepancies between SQLAlchemy models, Alembic migrations, and database schema.
"""
import os
import pytest
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from app.database.session import Base
import app.models  # Ensure all models are registered
from tests.conftest import TEST_DATABASE_URL


def test_schema_matches_migrations():
    """
    Verifies that SQLAlchemy models and the migrated PostgreSQL database schema match exactly.
    Fails if there is ANY drift in columns, types, nullability, defaults, indexes, or constraints.
    Runs `alembic check` against the migrated database.
    """
    alembic_ini_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    if not os.path.exists(alembic_ini_path):
        alembic_ini_path = "/app/alembic.ini"

    cfg = Config(alembic_ini_path)
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    try:
        command.check(cfg)
    except Exception as exc:
        pytest.fail(f"Schema drift detected between SQLAlchemy models and migrations: {exc}")


def test_alembic_migration_revisions_consistent():
    """Verify that Alembic migrations form a single linear chain without branching or multiple heads."""
    alembic_ini_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    if not os.path.exists(alembic_ini_path):
        alembic_ini_path = "/app/alembic.ini"

    alembic_cfg = Config(alembic_ini_path)
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 Alembic head revision, got {heads}"
