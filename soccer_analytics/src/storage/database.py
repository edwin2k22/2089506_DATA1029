"""
Database connection and session management.

Provides database engine, session factory, and initialization utilities.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from contextlib import contextmanager

from .models import Base


class Database:
    """
    Database connection manager.
    
    Handles engine creation, session management, and schema initialization.
    Supports both SQLite (for development) and PostgreSQL (for production).
    """
    
    def __init__(self, database_url: str):
        """
        Initialize database connection.
        
        Args:
            database_url: SQLAlchemy database URL
                - SQLite: sqlite:///./data/soccer_analytics.db
                - PostgreSQL: postgresql://user:pass@host:port/dbname
        """
        self.database_url = database_url
        
        # Engine configuration
        connect_args = {}
        if database_url.startswith('sqlite'):
            connect_args['check_same_thread'] = False
        
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before use
            connect_args=connect_args,
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
    
    def init_db(self) -> None:
        """
        Create all tables in the database.
        
        Safe to call multiple times - only creates missing tables.
        """
        Base.metadata.create_all(bind=self.engine)
    
    def drop_db(self) -> None:
        """
        Drop all tables from the database.
        
        WARNING: This will delete all data!
        """
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Usage:
            with db.get_session() as session:
                # use session
                session.commit()
        
        Automatically handles rollback on exceptions.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def check_connection(self) -> bool:
        """
        Verify database connection is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


# Global database instance (initialized in main app)
db: Database = None


def get_database(database_url: str) -> Database:
    """
    Get or create database instance.
    
    Args:
        database_url: Database connection URL
    
    Returns:
        Database instance
    """
    global db
    if db is None:
        db = Database(database_url)
    return db


def get_session() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_session)):
            ...
    """
    if db is None:
        raise RuntimeError("Database not initialized. Call get_database() first.")
    
    with db.get_session() as session:
        yield session
