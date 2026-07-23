"""
Database Connection Module — SQLAlchemy Engine & Session Factory.

Provides a shared SQLAlchemy ``Engine`` and ``SessionLocal`` factory
configured via the ``DATABASE_URL`` environment variable, with a
sensible default for local development. Exposes a ``get_db`` generator
for use as a FastAPI dependency.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Connection string — overridable via environment variable so the same
# code works in Docker Compose (where the host is the service name)
# and in local development (where the host is localhost).
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:secret@localhost:5432/maintain_db")

# Engine is the core interface to the database. It holds the connection pool.
engine = create_engine(DB_URL)

# SessionLocal is a sessionmaker bound to this engine.
# ``autocommit=False`` ensures changes are explicitly committed.
# ``autoflush=False`` prevents unexpected flushes mid-transaction.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI-compatible dependency that yields a DB session and ensures it
    is closed after the request completes.

    Usage
    -----
    .. code-block:: python

        from fastapi import Depends
        from database.db import get_db
        from sqlalchemy.orm import Session

        @router.get("/items")
        async def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
