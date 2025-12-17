"""Database configuration and session management."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Database path - store in data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'conversations.db')}"

# Create engine with optimized pooling settings for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Required for SQLite with async
        "timeout": 30  # Wait up to 30 seconds for lock
    },
    poolclass=StaticPool,  # StaticPool for SQLite - maintains single connection
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL debugging
)

# Enable Write-Ahead Logging for better concurrent performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance and concurrency."""
    cursor = dbapi_conn.cursor()
    # Enable WAL mode for better concurrent read/write performance
    cursor.execute("PRAGMA journal_mode=WAL")
    # Increase cache size to 10MB (default is usually 2MB)
    cursor.execute("PRAGMA cache_size=-10000")
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from . import models  # Import models to register them
    Base.metadata.create_all(bind=engine)
