import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME     = os.getenv("DB_NAME", "collabtool")
DB_USER     = os.getenv("DB_USER", os.environ.get("USER"))
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")

# SQLAlchemy engine (PostgreSQL) with connection pooling
try:
    engine = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        future=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True,  # Verify connection is still alive before using
        poolclass=QueuePool
    )
    
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        
except SQLAlchemyError as e:
    logger.error(f"Database connection failed: {str(e)}")
    # Create a dummy engine that will raise appropriate errors when used
    engine = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        future=True
    )

# Event listener to handle connection errors
@event.listens_for(engine, "connect", insert=True)
def ping_connection(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
    except Exception:
        # Reconnect if connection is invalid
        logger.warning("Database connection invalid, reconnecting...")
        connection_record.connection = None
        raise

# "SessionLocal" factory to produce Session objects
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Base class for all ORM models
Base = declarative_base()
