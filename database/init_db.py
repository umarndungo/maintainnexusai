"""
Database Initialisation — Create Tables on Startup.

Called by the FastAPI lifespan event and the Celery worker startup signal
so tables are guaranteed to exist before any code attempts to read/write.
"""

import logging
from database.db import engine
from database.models import Base

logger = logging.getLogger(__name__)


def init_database():
    """
    Create all tables defined in ``database.models`` if they do not exist.

    Safe to call repeatedly — ``create_all`` checks internal existence
    tracking and skips existing tables.
    """
    logger.info("Initialising database tables…")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")
