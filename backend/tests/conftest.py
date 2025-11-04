# === tests/conftest.py ===
# ruff: noqa: I001

from pathlib import Path
import os
import asyncio
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from api.main import app
from core.deps import get_db


env_path = Path(__file__).resolve().parents[1] / ".env.test"
load_dotenv(env_path)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

TEST_DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
INIT_SQL = Path(__file__).resolve().parents[1] / "init_db.sql"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Provide a global asyncio event loop for all tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Provide a shared async SQLAlchemy engine for the test session."""
    engine = create_async_engine(TEST_DB_URL, echo=False, future=True, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(engine):
    """Initialize a clean test database from init_db.sql."""
    print("🧩 Initializing test database schema (from init_db.sql)")
    sql_path = Path(__file__).resolve().parents[1] / "init_db.sql"
    sql_text = sql_path.read_text(encoding="utf-8")

    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE;")
        await conn.exec_driver_sql("CREATE SCHEMA public;")
        await conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "postgis";')
        await conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
        await conn.exec_driver_sql("SET search_path TO public;")

        stmts = []
        current = []
        in_func = False
        for line in sql_text.splitlines():
            if line.strip().startswith("--") or not line.strip():
                continue
            current.append(line)
            if "$$" in line:
                in_func = not in_func
            if not in_func and line.strip().endswith(";"):
                stmts.append("\n".join(current).strip())
                current = []
        if current:
            stmts.append("\n".join(current).strip())

        for stmt in stmts:
            try:
                await conn.exec_driver_sql(stmt)
            except Exception as e:
                print(f"⚠️ Skipped statement:\n{stmt[:120]}...\n{type(e).__name__}: {e}\n")

    yield


@pytest_asyncio.fixture()
async def db_session(engine):
    """Provide a fresh async database session per test."""
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_session):
    """Provide a FastAPI async test client with overridden DB dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clear_users_table(db_session):
    """Truncate the user table after each test to prevent duplicates."""
    await db_session.execute(text('TRUNCATE TABLE "user" RESTART IDENTITY CASCADE;'))
    await db_session.commit()
