"""Tests — conftest: shared fixtures for backend tests with real PostgreSQL and Alembic migrations."""
import os
import re
import asyncio
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
import asyncpg

from alembic import command
from alembic.config import Config

from app.main import app as fastapi_app
from app.database.session import get_db_session
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.rule import Rule
import app.models  # noqa: F401

# Resolve test database URL pointing to real PostgreSQL instance
raw_url = os.getenv("TEST_DATABASE_URL")
if not raw_url:
    raw_url = re.sub(r"/[^/]+$", "/legal_metrology_test_db", settings.DATABASE_URL)
TEST_DATABASE_URL = raw_url

from sqlalchemy.pool import NullPool

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


fastapi_app.dependency_overrides[get_db_session] = override_get_db


async def _ensure_test_database_exists(url: str):
    """Ensure the target PostgreSQL test database exists on the PostgreSQL server."""
    m = re.match(r"postgresql(?:\+asyncpg)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)", url)
    if not m:
        return
    user, password, host, port_str, dbname = m.groups()
    port = int(port_str) if port_str else 5432
    try:
        conn = await asyncpg.connect(
            user=user, password=password, host=host, port=port, database="postgres"
        )
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", dbname
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{dbname}" OWNER "{user}"')
        await conn.close()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """Build the test database schema using Alembic migrations, not models."""
    await _ensure_test_database_exists(TEST_DATABASE_URL)

    alembic_ini_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    if not os.path.exists(alembic_ini_path):
        alembic_ini_path = "/app/alembic.ini"

    cfg = Config(alembic_ini_path)
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    # Run migrations to head
    command.upgrade(cfg, "head")

    # Seed rules so rule engine DB queries have active rules to check against
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "rule-engine", "rules", "rules.json"),
        "/rule-engine/rules/rules.json",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "rule-engine", "rules", "rules.json")),
    ]
    rules_path = next((p for p in possible_paths if os.path.exists(p)), None)
    if rules_path:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_data = json.load(f)

        async with TestSessionFactory() as session:
            for rule_data in rules_data:
                res = await session.execute(
                    select(Rule).where(Rule.rule_id == rule_data["rule_id"])
                )
                if not res.scalar_one_or_none():
                    rule = Rule(
                        rule_id=rule_data["rule_id"],
                        field=rule_data["field"],
                        category=rule_data.get("category"),
                        mandatory=rule_data.get("mandatory", True),
                        severity=rule_data.get("severity", "HIGH"),
                        description=rule_data["description"],
                        validation_logic=rule_data.get("validation_logic"),
                        legal_reference=rule_data.get("legal_reference"),
                        rule_version=rule_data.get("rule_version", "1.0"),
                        package_type=rule_data.get("package_type", "retail"),
                        citation_verified=rule_data.get("citation_verified", False),
                    )
                    session.add(rule)
            await session.commit()

    yield

    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_data(setup_db):
    """Clean transactional tables between tests to guarantee test isolation."""
    yield
    async with TestSessionFactory() as session:
        try:
            await session.execute(
                text("TRUNCATE TABLE declarations, violations, ocr_regions, reports, inspection_images, inspections, products CASCADE;")
            )
            await session.execute(
                text("DELETE FROM users WHERE email LIKE '%@test.com';")
            )
            await session.commit()
        except Exception:
            await session.rollback()


@pytest_asyncio.fixture
async def db_session(setup_db):
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(setup_db):
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    result = await db_session.execute(select(User).where(User.email == "testadmin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email="testadmin@test.com",
            hashed_password=hash_password("TestAdmin@123"),
            full_name="Test Admin",
            role="ADMIN",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inspector_user(db_session: AsyncSession):
    result = await db_session.execute(select(User).where(User.email == "testinspector@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email="testinspector@test.com",
            hashed_password=hash_password("TestInspector@123"),
            full_name="Test Inspector",
            role="INSPECTOR",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testadmin@test.com", "password": "TestAdmin@123"},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def inspector_token(client, inspector_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testinspector@test.com", "password": "TestInspector@123"},
    )
    return resp.json()["access_token"]
