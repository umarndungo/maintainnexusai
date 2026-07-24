"""
Database Initialisation — Create Tables and Apply Safe Schema Updates on Startup.

Called by the FastAPI lifespan event and the Celery worker startup signal
so the database schema is created and updated before any code attempts to read/write.
"""

import logging
from sqlalchemy import inspect, text
from database.db import engine
from database.models import Base

logger = logging.getLogger(__name__)


def _ensure_work_orders_alert_task_id_column():
    """Add the alert_task_id column to work_orders if it is missing."""
    inspector = inspect(engine)
    if "work_orders" not in inspector.get_table_names():
        return

    column_names = [column["name"] for column in inspector.get_columns("work_orders")]
    if "alert_task_id" in column_names:
        return

    logger.info("Adding missing work_orders.alert_task_id column to existing database.")
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE work_orders ADD COLUMN alert_task_id VARCHAR")
        )


def init_database():
    """
    Create all tables defined in ``database.models`` if they do not exist.

    Safe to call repeatedly — ``create_all`` checks internal existence
    tracking and skips existing tables.
    """
    logger.info("Initialising database tables…")
    Base.metadata.create_all(bind=engine)
    _ensure_work_orders_alert_task_id_column()
    logger.info("Database tables verified.")
