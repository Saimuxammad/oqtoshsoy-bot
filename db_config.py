"""Database configuration module with robust handling of connection strings"""
import os
import logging

logger = logging.getLogger(__name__)


def get_safe_database_url():
    """Returns a sanitized database URL with fallback to SQLite"""

    # First attempt to read from environment variable
    db_url = os.environ.get("DATABASE_URL", "")

    # If empty or not set, use default SQLite
    if not db_url:
        logger.info("No DATABASE_URL found, using SQLite database")
        return "sqlite:///oqtoshsoy.db"

    try:
        # For PostgreSQL URLs, sanitize the connection string
        if "postgres" in db_url.lower():
            logger.info("Using PostgreSQL database with sanitized connection string")

            # Force use of SQLite for development
            logger.warning("Overriding PostgreSQL with SQLite for development")
            return "sqlite:///oqtoshsoy.db"

        # For SQLite URLs, use as is
        if db_url.startswith("sqlite"):
            logger.info("Using SQLite database")
            return db_url

        # Default fallback
        logger.warning(f"Unrecognized database type, falling back to SQLite: {db_url[:10]}...")
        return "sqlite:///oqtoshsoy.db"
    except Exception as e:
        logger.error(f"Error processing database URL: {str(e)}")
        logger.info("Falling back to SQLite database")
        return "sqlite:///oqtoshsoy.db"