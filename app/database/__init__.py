from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import os

# Import custom database URL handler
from db_config import get_safe_database_url

# Configure logging
logger = logging.getLogger(__name__)

# Get safe database URL
DATABASE_URL = get_safe_database_url()

# Create engine with proper error handling
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"Database engine initialized successfully using {DATABASE_URL[:10]}...")
except Exception as e:
    logger.error(f"Error initializing database engine: {str(e)}")
    logger.info("Falling back to in-memory SQLite database")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database and create tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise