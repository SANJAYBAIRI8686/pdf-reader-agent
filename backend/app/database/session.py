from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Determine database connection arguments based on driver
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create the synchronous SQLAlchemy engine
# (Designing for synchronous database access via SQLAlchemy for standard simplicity,
# fully compatible with PostgreSQL pools later)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True  # Detect and recover from stale/dropped connections
)

# Session factory for generating database transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """
    Dependency helper that yields a database session and ensures it is closed
    after the request completes. Used for FastAPI Dependency Injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
