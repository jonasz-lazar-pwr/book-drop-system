# === tests/conftest.py ===
# ruff: noqa: I001, E402

from pathlib import Path
import os
from dotenv import load_dotenv

# --- Environment setup ---
env_path = Path(__file__).resolve().parents[1] / ".env.test"
load_dotenv(env_path, override=True)

import asyncio
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import text, select
from fastapi import Request, HTTPException, status

from api.main import app
from core.deps import get_db, get_current_user
from core.security import verify_token
from models import User

from core.security import hash_password
from core.security import create_access_token


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
async def clear_test_data(db_session):
    """Truncate main data tables before each test to ensure full isolation."""
    truncate_sql = """
    TRUNCATE TABLE
        "user",
        book_item,
        book,
        cart_item,
        cart,
        locker,
        locker_box,
        locker_shipment,
        "order",
        order_item
    RESTART IDENTITY CASCADE;
    """
    await db_session.execute(text(truncate_sql))
    await db_session.commit()


@pytest_asyncio.fixture(autouse=True)
async def override_auth(client, db_session):
    """Override get_current_user to support both test-UUID and real JWT tokens."""

    async def fake_get_current_user(request: Request):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        token = auth.replace("Bearer ", "").strip()

        # Case 1: test token (used in cart tests)
        if token.startswith("test-"):
            user_id = token.replace("test-", "")
        else:
            # Case 2: real JWT (used in /auth/me)
            decoded = verify_token(token)
            if not decoded or "sub" not in decoded:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            user_id = decoded["sub"]

        user = await db_session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return user

    app.dependency_overrides[get_current_user] = fake_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ============================================
# LIBRARIAN & READER FIXTURES
# ============================================


@pytest_asyncio.fixture
async def reader_user(db_session: AsyncSession) -> User:
    """Create a test reader user."""

    user = User(
        email="reader@test.com",
        password=hash_password("testpassword"),
        first_name="Test",
        last_name="Reader",
        role="reader",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def librarian_user(db_session: AsyncSession) -> User:
    """Create a test librarian user."""

    user = User(
        email="librarian@test.com",
        password=hash_password("testpassword"),
        first_name="Test",
        last_name="Librarian",
        role="librarian",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def reader_token(reader_user: User) -> str:
    """Get authentication token for reader."""
    user_data = {
        "id": reader_user.id,
        "email": reader_user.email,
        "role": reader_user.role,
        "first_name": reader_user.first_name,
        "last_name": reader_user.last_name,
    }
    return create_access_token(user_data)


@pytest_asyncio.fixture
def librarian_token(librarian_user: User) -> str:
    """Get authentication token for librarian."""
    user_data = {
        "id": librarian_user.id,
        "email": librarian_user.email,
        "role": librarian_user.role,
        "first_name": librarian_user.first_name,
        "last_name": librarian_user.last_name,
    }
    return create_access_token(user_data)
