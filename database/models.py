"""
SQLAlchemy ORM Models — Database Schema Definition.

Defines the two core tables used by MaintainNexus:

- ``work_orders``  — persists every dispatched work order with full
                     equipment, technician, and lifecycle metadata.
- ``audit_logs``   — append-only event store that records every
                     pipeline execution (what happened, when, and the
                     payload that triggered it).
"""

from sqlalchemy import Boolean, Column, String, Integer, DateTime, Float, ForeignKey, Text, Index
from sqlalchemy.orm import declarative_base
import datetime

# Declarative base — every model class inherits from this.
Base = declarative_base()


class StaffCredential(Base):
    """Persisted password credentials for every human login identity."""

    __tablename__ = "staff_credentials"

    user_id = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    technician_id = Column(String, nullable=True)
    must_change_password = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


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

    # Close-out fields (populated by PATCH .../complete) — see api/workorders.py.
    completion_notes = Column(Text, nullable=True)
    parts_used = Column(String, nullable=True)
    photo_object_path = Column(String, nullable=True)


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


class TechnicianDevice(Base):
    """The most recent FCM push token registered for a technician.

    One row per technician — a fresh sign-in on a new device just
    overwrites the previous token. The HR technician roster itself is
    still an in-memory stand-in (see api/technicians.py); this table is
    the one piece of technician-related state that genuinely needs to
    survive a restart, so it's real Postgres rather than in-memory.
    """

    __tablename__ = "technician_devices"

    technician_id = Column(String, primary_key=True)
    device_token = Column(String, nullable=False)
    platform = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class SmsLog(Base):
    """Append-only record of every outbound SMS send attempt.

    Kept even when Africa's Talking credentials are absent (status
    ``SKIPPED_NO_CREDENTIALS``) so the dispatch flow's notification
    behavior is visible in the same place whether or not a real
    provider is wired up yet.
    """

    __tablename__ = "sms_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_order_id = Column(String, nullable=True)
    recipient = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    provider_message_id = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class PendingSmsPrompt(Base):
    """An outstanding 'reply 1/3 to accept/complete' prompt sent to a
    non-smartphone technician (spec Phase 3). Matched on phone number +
    the exact code echoed back, not "most recent open prompt" — a
    technician can have more than one job in flight.
    """

    __tablename__ = "pending_sms_prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, nullable=False)
    work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=False)
    expected_codes = Column(String, nullable=False)  # comma-separated, e.g. "1,3"
    code_to_status = Column(String, nullable=False)  # JSON: {"1": "IN_PROGRESS", "3": "COMPLETED"}
    sent_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_pending_sms_prompt_phone", "phone_number", "resolved_at"),
    )


class EquipmentReading(Base):
    """One telemetry reading, ETL-loaded *before* ML ever sees it.

    Row lifecycle: inserted unscored by the telemetry ETL's Load step
    (etl/telemetry_pipeline.py), then updated in place once ML scoring
    returns a result. A mutable operational table, not part of the hash
    chain — same pattern as WorkOrderRecord's mutable completion_notes
    column; audit_logs remains the append-only, hash-chained trail and
    is written independently of this table.

    This is the single structured source api.monitoring reads from —
    replaces re-parsing audit_logs JSON for the equipment-monitoring
    endpoints.
    """

    __tablename__ = "equipment_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)  # PUMP / VALVE / LOADING_ARM
    station_id = Column(String, nullable=True)
    telemetry = Column(Text, nullable=False)  # JSON: the raw + enriched reading
    risk_probability = Column(Float, nullable=True)  # NULL until ML has scored it
    risk_level = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    top_features = Column(Text, nullable=True)  # JSON list
    alert_created = Column(Boolean, nullable=False, default=False)
    received_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_equipment_readings_equipment_id_received_at", "equipment_id", "received_at"),
    )


# ---------------------------------------------------------------------------
# Predict -> Decide -> Act -> Learn: the decision-engine tables.
#
# Deliberately simplified from the full docs/11-PRODUCT-CONTRACT.md schema
# for a first build (see etl/decision_engine.py's module docstring) — no
# standalone Truck entity, and LoadingPoint/LoadingSlot are lazily
# self-seeded at decision time rather than pre-populated, since the
# equipment fleet is randomized per-process (api/equipment.py) and a fixed
# seed can't reliably target whichever pump actually shows up in a given
# run's generated telemetry.
# ---------------------------------------------------------------------------

class LoadingPoint(Base):
    """One loading bay. ``equipment_id`` is the pump/valve/arm serving it —
    not a foreign key (equipment doesn't have its own table yet either;
    same string-matching convention as EquipmentReading/WorkOrderRecord)."""

    __tablename__ = "loading_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bay_code = Column(String, unique=True, nullable=False)
    equipment_id = Column(String, nullable=True)
    station_id = Column(String, nullable=True)
    supported_product = Column(String, nullable=False, default="DIESEL")
    capacity_status = Column(String, nullable=False, default="AVAILABLE")  # AVAILABLE / UNAVAILABLE


class LoadingSlot(Base):
    """A truck scheduled at a loading point. Reassignment moves
    ``loading_point_id`` to an alternate bay rather than mutating history —
    the row's own ``status`` records that it happened, and Decision/
    OperationalAction below carry the why."""

    __tablename__ = "loading_slots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    loading_point_id = Column(Integer, ForeignKey("loading_points.id"), nullable=False)
    truck_code = Column(String, nullable=False)
    scheduled_arrival = Column(DateTime(timezone=True), nullable=False)
    planned_volume = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="SCHEDULED")  # SCHEDULED / REASSIGNED / COMPLETED


class Decision(Base):
    """One decision-engine evaluation that resulted in an action.
    ``reading_id`` is this system's ``prediction_id`` — the EquipmentReading
    that triggered the evaluation (docs/10-ML-BACKEND-CONTRACT.md)."""

    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reading_id = Column(Integer, ForeignKey("equipment_readings.id"), nullable=True)
    decision_type = Column(String, nullable=False)  # REASSIGN_LOADING_POINT / RESCHEDULE_TRUCK / CREATE_MAINTENANCE_WORK_ORDER
    reason = Column(Text, nullable=False)
    affected_equipment_id = Column(String, nullable=False)
    requires_human_approval = Column(Boolean, nullable=False, default=False)
    policy_version = Column(String, nullable=False, default="automation-policy-1.0")
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class OperationalAction(Base):
    """The action taken for a Decision. ``idempotency_key`` is unique —
    same dedup discipline as WorkOrderRecord.alert_task_id — so retrying
    the same decision never applies it twice."""

    __tablename__ = "operational_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    action_type = Column(String, nullable=False)
    truck_code = Column(String, nullable=True)
    original_loading_point_id = Column(Integer, nullable=True)
    new_loading_point_id = Column(Integer, nullable=True)
    idempotency_key = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default="APPLIED")
    requested_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class OperationalOutcome(Base):
    """The Learn stage — what actually happened after an action. Written
    as a stub (only action_success known) at action time; the rest is
    filled in later by a follow-up close-out step, which is out of scope
    for this first build (docs/14-PREDICT-DECIDE-ACT-LEARN.md §20: "model
    learning is not immediate")."""

    __tablename__ = "operational_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("operational_actions.id"), nullable=False)
    action_success = Column(Boolean, nullable=True)
    actual_failure = Column(Boolean, nullable=True)
    actual_delay_minutes = Column(Float, nullable=True)
    alternate_bay_completed = Column(Boolean, nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
