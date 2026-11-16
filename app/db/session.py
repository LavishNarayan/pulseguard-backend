from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

async_engine = create_async_engine(settings.ASYNC_DATABASE_URL, pool_size=20, max_overflow=10)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

sync_engine = create_engine(settings.SYNC_DATABASE_URL, pool_size=10, max_overflow=5)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
