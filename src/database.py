"""
Database Configuration and Connection Management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
import os
from typing import Generator

# Database URL from environment - REQUIRED
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required.\n"
        "Example: DATABASE_URL=postgresql://user:password@localhost:5432/dbname\n"
        "Set this in your .env file or environment before starting the application."
    )

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"  # SQL logging
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints
    Usage: def endpoint(db: Session = Depends(get_db))
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """
    Context manager for manual database access
    Usage: 
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """
    Initialize database - create all tables
    Run this once during deployment
    """
    from src.models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

def drop_all_tables():
    """
    Drop all tables - USE WITH CAUTION
    Only for development/testing
    """
    from src.models import Base
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All tables dropped")

def reset_db():
    """
    Drop and recreate all tables
    USE ONLY IN DEVELOPMENT
    """
    drop_all_tables()
    init_db()