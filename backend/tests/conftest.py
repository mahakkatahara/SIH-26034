"""Tests — conftest: shared fixtures for backend tests."""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database.session import Base, get_db_session
from app.core.security import hash_password
from app.models.user import User

# Use SQLite for tests (in-memory, no PostgreSQL required)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db_session] = override_get_db


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_db):
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(setup_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
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
