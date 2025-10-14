# === db/session.py ===

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from core.config import settings

# Build the database URL from environment settings
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# Create an async SQLAlchemy engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,      # Check if connections are alive before using them
    pool_size=5,             # Initial number of connections in the pool
    max_overflow=10,         # Max number of connections to create beyond the pool size
    pool_timeout=30,         # Max wait time for a connection from the pool
    pool_recycle=1800,       # Refresh the connection every 30 minutes
)

# Create an async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
