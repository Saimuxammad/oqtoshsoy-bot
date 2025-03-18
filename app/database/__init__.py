from sqlalchemy.orm import sessionmaker, declarative_base
import logging
import os

# Import custom database URL handler
from db_config import get_safe_database_url

# Configure logging
logger = logging.getLogger(__name__)

# Get safe database URL
DATABASE_URL = get_safe_database_url()

# Check if we can use async SQLAlchemy
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

    USE_ASYNC = True
except ImportError:
    from sqlalchemy import create_engine

    USE_ASYNC = False
    logger.warning("AsyncIO SQLAlchemy extensions not available, falling back to sync mode")

# Create engine based on available packages
try:
    if USE_ASYNC:
        # Try to use async engine if possible
        try:
            import aiosqlite

            # Convert URL for async use
            async_url = DATABASE_URL
            if async_url.startswith("sqlite"):
                async_url = async_url.replace("sqlite:", "sqlite+aiosqlite:")
            elif async_url.startswith("postgresql"):
                async_url = async_url.replace("postgresql:", "postgresql+asyncpg:")

            # Create async engine
            engine = create_async_engine(
                async_url,
                echo=False,
                future=True
            )

            # Create async session factory
            SessionLocal = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            logger.info("Async database engine initialized successfully")


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

        except ImportError:
            # Fall back to sync mode if aiosqlite not available
            USE_ASYNC = False
            logger.warning("aiosqlite not available, falling back to sync SQLite")

    # Use synchronous engine if async not available
    if not USE_ASYNC:
        # Create synchronous engine
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        )

        # Create sync session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        logger.info("Synchronous database engine initialized successfully")


        def init_db():
            """Initialize database and create tables"""
            try:
                # Create all tables
                Base.metadata.create_all(bind=engine)

                logger.info("Database tables created successfully")
                return True
            except Exception as e:
                logger.error(f"Error creating database tables: {str(e)}")
                raise

except Exception as e:
    logger.error(f"Error initializing database engine: {str(e)}")
    logger.info("Falling back to in-memory SQLite database")

    # Create fallback engine (sync mode)
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


    def init_db():
        Base.metadata.create_all(bind=engine)
        logger.info("Fallback database tables created successfully")
        return True

# Create base class for models
Base = declarative_base()