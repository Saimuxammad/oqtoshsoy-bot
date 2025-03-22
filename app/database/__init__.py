from sqlalchemy.orm import sessionmaker, declarative_base
import logging
import os

# Import custom database URL handler
from db_config import get_safe_database_url

# Configure logging
logger = logging.getLogger(__name__)

# Get safe database URL
DATABASE_URL = get_safe_database_url()

# Create base class for models
Base = declarative_base()

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
            AsyncSessionLocal = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Export session factory as SessionLocal
            SessionLocal = AsyncSessionLocal

            logger.info("Async database engine initialized successfully")


            async def get_db():
                """Dependency for database session"""
                async with AsyncSessionLocal() as session:
                    yield session


            async def init_db(force_recreate=False):
                """Initialize database and create tables

                Args:
                    force_recreate (bool): If True, drop existing tables and recreate them
                """
                try:
                    # Import models to ensure they are registered with Base
                    from app.database.models import User, Room, Booking, Review

                    # Create all tables
                    async with engine.begin() as conn:
                        if force_recreate:
                            # Drop all tables first if force_recreate is True
                            logger.info("Dropping all existing tables...")
                            await conn.run_sync(Base.metadata.drop_all)

                        # Create all tables
                        await conn.run_sync(Base.metadata.create_all)

                    logger.info("Database tables created successfully")

                    # Add sample data when initializing a fresh database
                    if force_recreate:
                        await add_sample_data()

                    return True
                except Exception as e:
                    logger.error(f"Error creating database tables: {str(e)}")
                    raise


            async def add_sample_data():
                """Add sample data to the database"""
                try:
                    from app.database.models import Room
                    from sqlalchemy import select

                    # Create a session
                    async with AsyncSessionLocal() as session:
                        # Check if there are already rooms
                        result = await session.execute(select(Room))
                        if result.scalars().first() is not None:
                            logger.info("Sample data already exists, skipping...")
                            return

                        # Add sample rooms
                        standard_room = Room(
                            name="Стандартный номер",
                            description="Уютный номер с видом на горы",
                            room_type="standard",
                            price_per_night=3000,
                            capacity=2,
                            is_available=True,
                            image_url="https://example.com/standard.jpg",
                            photos="[]",  # Empty JSON array
                            amenities='["Wi-Fi", "TV", "Холодильник"]'  # JSON array with amenities
                        )

                        luxury_room = Room(
                            name="Люкс",
                            description="Просторный номер люкс с отдельной гостиной",
                            room_type="luxury",
                            price_per_night=5000,
                            capacity=4,
                            is_available=True,
                            image_url="https://example.com/luxury.jpg",
                            photos="[]",
                            amenities='["Wi-Fi", "TV", "Холодильник", "Джакузи", "Мини-бар"]'
                        )

                        family_room = Room(
                            name="Семейный номер",
                            description="Большой номер для всей семьи",
                            room_type="family",
                            price_per_night=7000,
                            capacity=6,
                            is_available=True,
                            image_url="https://example.com/family.jpg",
                            photos="[]",
                            amenities='["Wi-Fi", "TV", "Холодильник", "Детская кроватка", "Игровая зона"]'
                        )

                        # Add rooms to session
                        session.add_all([standard_room, luxury_room, family_room])

                        # Commit the session
                        await session.commit()
                        logger.info("Sample data added successfully")
                except Exception as e:
                    logger.error(f"Error adding sample data: {str(e)}")
                    raise

        except ImportError:
            # Fall back to sync mode if aiosqlite not available
            USE_ASYNC = False
            logger.warning("aiosqlite not available, falling back to sync SQLite")

    # Use synchronous engine if async not available
    if not USE_ASYNC:
        from sqlalchemy import create_engine

        # Create synchronous engine
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        )

        # Create sync session factory
        SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Export session factory as SessionLocal
        SessionLocal = SyncSessionLocal

        logger.info("Synchronous database engine initialized successfully")


        def get_db():
            """Dependency for database session"""
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()


        def init_db(force_recreate=False):
            """Initialize database and create tables"""
            try:
                # Import models to ensure they are registered with Base
                from app.database.models import User, Room, Booking, Review

                if force_recreate:
                    # Drop all tables first if force_recreate is True
                    logger.info("Dropping all existing tables...")
                    Base.metadata.drop_all(bind=engine)

                # Create all tables
                Base.metadata.create_all(bind=engine)

                logger.info("Database tables created successfully")

                # Add sample data
                if force_recreate:
                    add_sample_data()

                return True
            except Exception as e:
                logger.error(f"Error creating database tables: {str(e)}")
                raise


        def add_sample_data():
            """Add sample data to the database"""
            try:
                from app.database.models import Room
                from sqlalchemy import select

                # Create a session
                with SyncSessionLocal() as session:
                    # Check if there are already rooms
                    if session.query(Room).first() is not None:
                        logger.info("Sample data already exists, skipping...")
                        return

                    # Add sample rooms
                    standard_room = Room(
                        name="Стандартный номер",
                        description="Уютный номер с видом на горы",
                        room_type="standard",
                        price_per_night=3000,
                        capacity=2,
                        is_available=True,
                        image_url="https://example.com/standard.jpg",
                        photos="[]",  # Empty JSON array
                        amenities='["Wi-Fi", "TV", "Холодильник"]'  # JSON array with amenities
                    )

                    luxury_room = Room(
                        name="Люкс",
                        description="Просторный номер люкс с отдельной гостиной",
                        room_type="luxury",
                        price_per_night=5000,
                        capacity=4,
                        is_available=True,
                        image_url="https://example.com/luxury.jpg",
                        photos="[]",
                        amenities='["Wi-Fi", "TV", "Холодильник", "Джакузи", "Мини-бар"]'
                    )

                    family_room = Room(
                        name="Семейный номер",
                        description="Большой номер для всей семьи",
                        room_type="family",
                        price_per_night=7000,
                        capacity=6,
                        is_available=True,
                        image_url="https://example.com/family.jpg",
                        photos="[]",
                        amenities='["Wi-Fi", "TV", "Холодильник", "Детская кроватка", "Игровая зона"]'
                    )

                    # Add rooms to session
                    session.add_all([standard_room, luxury_room, family_room])

                    # Commit the session
                    session.commit()
                    logger.info("Sample data added successfully")
            except Exception as e:
                logger.error(f"Error adding sample data: {str(e)}")
                raise

except Exception as e:
    logger.error(f"Error initializing database engine: {str(e)}")
    logger.info("Falling back to in-memory SQLite database")

    # Create fallback engine (sync mode)
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


    def get_db():
        """Dependency for database session"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


    def init_db(force_recreate=False):
        # Import models to ensure they are registered with Base
        from app.database.models import User, Room, Booking, Review

        Base.metadata.create_all(bind=engine)
        logger.info("Fallback database tables created successfully")

        # Add sample data
        add_sample_data()

        return True


    def add_sample_data():
        """Add sample data to the database"""
        try:
            from app.database.models import Room

            # Create a session
            with SessionLocal() as session:
                # Check if there are already rooms
                if session.query(Room).first() is not None:
                    logger.info("Sample data already exists, skipping...")
                    return

                # Add sample rooms
                standard_room = Room(
                    name="Стандартный номер",
                    description="Уютный номер с видом на горы",
                    room_type="standard",
                    price_per_night=3000,
                    capacity=2,
                    is_available=True,
                    image_url="https://example.com/standard.jpg",
                    photos="[]",  # Empty JSON array
                    amenities='["Wi-Fi", "TV", "Холодильник"]'  # JSON array with amenities
                )

                luxury_room = Room(
                    name="Люкс",
                    description="Просторный номер люкс с отдельной гостиной",
                    room_type="luxury",
                    price_per_night=5000,
                    capacity=4,
                    is_available=True,
                    image_url="https://example.com/luxury.jpg",
                    photos="[]",
                    amenities='["Wi-Fi", "TV", "Холодильник", "Джакузи", "Мини-бар"]'
                )

                family_room = Room(
                    name="Семейный номер",
                    description="Большой номер для всей семьи",
                    room_type="family",
                    price_per_night=7000,
                    capacity=6,
                    is_available=True,
                    image_url="https://example.com/family.jpg",
                    photos="[]",
                    amenities='["Wi-Fi", "TV", "Холодильник", "Детская кроватка", "Игровая зона"]'
                )

                # Add rooms to session
                session.add_all([standard_room, luxury_room, family_room])

                # Commit the session
                session.commit()
                logger.info("Sample data added successfully")
        except Exception as e:
            logger.error(f"Error adding sample data: {str(e)}")
            raise


@app.get("/fix-connection")
async def fix_connection():
    """Fix the database connection by updating the engine"""
    try:
        import sqlite3
        import os
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.database import engine

        # 1. Get the absolute path for the database
        from app.config import DATABASE_URL

        # Extract file path from SQLite URL
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL[10:]
        else:
            db_path = DATABASE_URL

        # Make the path absolute
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)

        # 2. Check if the database exists and has tables
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            if "rooms" in tables:
                # 3. Create a new engine with the correct path
                new_url = f"sqlite+aiosqlite:///{db_path}"
                global engine
                engine = create_async_engine(new_url, echo=False, future=True)

                # 4. Update any global engine references
                import app.database
                app.database.engine = engine

                return {
                    "status": "success",
                    "message": "База данных успешно подключена",
                    "database_path": db_path,
                    "tables": tables
                }
            else:
                return {
                    "status": "error",
                    "message": "База данных существует, но таблица 'rooms' не найдена",
                    "tables": tables
                }
        else:
            return {
                "status": "error",
                "message": f"База данных по пути {db_path} не существует"
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}