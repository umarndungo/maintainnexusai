"""
SQLAlchemy ORM Models — Database Schema Definition.

Defines the two core tables used by MaintainNexus:

- ``work_orders``  — persists every dispatched work order with full
                     equipment, technician, and lifecycle metadata.
- ``audit_logs``   — append-only event store that records every
                     pipeline execution (what happened, when, and the
                     payload that triggered it).
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import declarative_base
import datetime

# Declarative base — every model class inherits from this.
Base = declarative_base()


class WorkOrderRecord(Base):
    """
    Represents a work order dispatched to a technician.

    Columns
    -------
    id : str
        Primary key — unique work-order identifier (e.g. ``WO-A1B2C3D4``).
    equipment_id : str
        Foreign-key reference to the asset being repaired (not enforced
        by a constraint in this mock schema).
    technician_id : str
        The technician assigned to this work order.
    part_number : str
        The replacement part that was reserved for the job.
    created_at : datetime
        Timestamp of when this record was inserted (UTC).
    """
    __tablename__ = "work_orders"

    id = Column(String, primary_key=True)
    equipment_id = Column(String, nullable=False)
    technician_id = Column(String, nullable=False)
    part_number = Column(String, nullable=False)
    alert_task_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class WorkOrderLifecycleEvent(Base):
    """Immutable, hash-chained transition in a work-order lifecycle."""

    __tablename__ = "work_order_lifecycle_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    note = Column(Text, nullable=True)
    event_hash = Column(String(64), nullable=False, unique=True)
    previous_event_hash = Column(String(64), nullable=False)
    supersedes_event_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_lifecycle_work_order_timestamp", "work_order_id", "timestamp"),
    )


class AuditLog(Base):
    """
    Append-only event log recording all pipeline activity.

    Every time the ETL pipeline processes an alert (success or failure),
    an ``AuditLog`` row is inserted so operators can trace what happened.

    Columns
    -------
    id : int (auto-increment)
        Surrogate primary key.
    event_name : str
        Short label identifying the event (e.g. ``"ALERT_RECEIVED"``,
        ``"WORK_ORDER_CREATED"``).
    payload : str
        JSON-serialised string of the event's data payload.
    timestamp : datetime
        When the event occurred (UTC).
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    event_hash = Column(String(64), nullable=True, unique=True)
    previous_event_hash = Column(String(64), nullable=True)
    supersedes_event_id = Column(Integer, nullable=True)


class DowntimeWindow(Base):
    """Equipment downtime interval opened and closed by lifecycle transitions."""

    __tablename__ = "downtime_windows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String, nullable=False)
    work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    cause_alert_id = Column(String, nullable=True)
