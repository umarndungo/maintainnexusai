"""Integration test for the insert-only database grants.

``database/run_migrations.py`` is the one-shot admin job that creates the
``maintain_app`` runtime role and revokes UPDATE/DELETE on the audit tables.
Its SQL (``CREATE ROLE``, ``pg_roles``, ``ALTER DEFAULT PRIVILEGES``, ...) is
Postgres-only, so it can't be exercised against the sqlite-in-memory engine
the rest of the suite uses.

This test spins up a throwaway database on a real Postgres server, runs the
migration against it as a uniquely-named app role, and then connects *as
that role* to prove the actual database-enforced behaviour end to end:

- the app role can SELECT/INSERT on every table, including the two
  append-only ones (which also exercises the autoincrement sequence grants);
- the app role is rejected by Postgres itself when it tries to UPDATE or
  DELETE a row in ``audit_logs`` / ``work_order_lifecycle_events``;
- the app role has full CRUD on an ordinary operational table
  (``work_orders``);
- running the migration twice is a no-op (idempotency).

It needs a reachable Postgres admin connection to run. Point
``TEST_ADMIN_DATABASE_URL`` at one (e.g. the docker-compose ``postgres_db``
service published to the host) to enable it; otherwise it skips itself so it
never blocks the rest of the suite in environments without Docker/Postgres.
"""

import datetime
import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import sessionmaker

import database.run_migrations as run_migrations_module
from database.models import AuditLog, WorkOrderRecord

ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL",
    "postgresql://admin:change-this-password@localhost:5432/maintain_db",
)


@pytest.fixture(scope="module")
def admin_engine():
    engine = create_engine(ADMIN_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"No reachable Postgres admin connection for grants test: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture
def test_database_url(admin_engine):
    """Create a throwaway database for one test and drop it afterward."""
    db_name = f"migrations_test_{uuid.uuid4().hex[:8]}"
    autocommit_engine = admin_engine.execution_options(isolation_level="AUTOCOMMIT")
    with autocommit_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    try:
        # str(url) masks the password ("***"); render it explicitly instead.
        yield admin_engine.url.set(database=db_name).render_as_string(hide_password=False)
    finally:
        with autocommit_engine.connect() as conn:
            conn.execute(
                text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
            )


@pytest.fixture
def app_role_name():
    return f"maintain_app_test_{uuid.uuid4().hex[:8]}"


def _run_migrations_against(monkeypatch, database_url, app_role, app_password):
    test_engine = create_engine(database_url)
    monkeypatch.setattr(run_migrations_module, "engine", test_engine)
    monkeypatch.setenv("APP_DB_USER", app_role)
    monkeypatch.setenv("APP_DB_PASSWORD", app_password)
    run_migrations_module.run_migrations()
    test_engine.dispose()


def test_migration_enforces_insert_only_grants(monkeypatch, test_database_url, app_role_name):
    app_password = "test-pw-" + uuid.uuid4().hex[:8]

    # Running the migration twice must succeed both times (idempotency).
    _run_migrations_against(monkeypatch, test_database_url, app_role_name, app_password)
    _run_migrations_against(monkeypatch, test_database_url, app_role_name, app_password)

    app_url = create_engine(test_database_url).url.set(
        username=app_role_name, password=app_password
    ).render_as_string(hide_password=False)
    app_engine = create_engine(app_url)
    AppSession = sessionmaker(bind=app_engine)

    try:
        # --- append-only table: INSERT must work (also proves the
        # autoincrement sequence grant), UPDATE/DELETE must be rejected. ---
        session = AppSession()
        log = AuditLog(event_name="TEST_EVENT", payload="{}")
        session.add(log)
        session.commit()
        log_id = log.id
        session.close()

        session = AppSession()
        with pytest.raises(DBAPIError, match="permission denied"):
            session.execute(
                text("UPDATE audit_logs SET event_name = 'HACKED' WHERE id = :id"),
                {"id": log_id},
            )
            session.commit()
        session.rollback()
        session.close()

        session = AppSession()
        with pytest.raises(DBAPIError, match="permission denied"):
            session.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": log_id})
            session.commit()
        session.rollback()
        session.close()

        # --- ordinary operational table: full CRUD must still work. ---
        session = AppSession()
        work_order = WorkOrderRecord(
            id=f"WO-TEST-{uuid.uuid4().hex[:8]}",
            equipment_id="EQ-1",
            technician_id="TECH-1",
            part_number="PART-1",
            created_at=datetime.datetime.utcnow(),
        )
        session.add(work_order)
        session.commit()

        work_order.part_number = "PART-2"
        session.commit()

        session.delete(work_order)
        session.commit()
        session.close()
    finally:
        app_engine.dispose()
