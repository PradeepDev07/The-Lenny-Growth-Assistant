from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from backend.app.config import settings

# Determine connect_args based on DB dialect
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Create Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args
)

# Crucial for SQLite: by default SQLite disables Foreign Key enforcement.
# We must execute PRAGMA foreign_keys = ON on connection so ON DELETE CASCADE functions.
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.
    Rolls back automatically on unhandled exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Creates all tables on startup if they do not already exist.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
