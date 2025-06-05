import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_NAME     = os.getenv("DB_NAME", "collabtool")
DB_USER     = os.getenv("DB_USER", os.environ.get("USER"))
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")

# SQLAlchemy engine (PostgreSQL)
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    future=True
)

# “SessionLocal” factory to produce Session objects
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Base class for all ORM models
Base = declarative_base()
