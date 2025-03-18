from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import logging
import os

# Import custom database URL handler
from db_config import get_safe_database_url

# Configure logging
logger = logging.getLogger(__name__)

# Get safe database URL
DATABASE_URL = get_safe_database_url()

# Create async engine (convert URL if needed)
async_url = DATABASE_URL
if async_url.startswith("sqlite"):
    async_url = async_url.replace("sqlite:", "sqlite+aiosqlite:")
elif async_url.startswith("postgresql"):
    async_url = async_url.replace("postgresql:", "postgresql+asyncpg:")

try:
    # Create async engine
    engine = create_async_engine(
        async_url,
        echo=False,
        future=True
    )

    # Create async session factory
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    logger.info(f"Async database engine initialized successfully")
except Exception as e:
    logger.error(f"Error initializing async database engine: {str(e)}")
    logger.info("Falling back to in-memory SQLite database")
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

Base = declarative_base()


async def get_db():
    """Dependency for database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Initialize database and create tables"""
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise