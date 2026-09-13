"""Run schema creation and database grants as the PostgreSQL admin role."""

import os
import re

from sqlalchemy import inspect, text

from database.db import engine
from database.models import Base

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _identifier(value: str, name: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {name}: {value!r}")
    return value


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _ensure_legacy_columns(connection) -> None:
    inspector = inspect(connection)
    if "work_orders" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("work_orders")}
        if "alert_task_id" not in columns:
            connection.execute(text("ALTER TABLE work_orders ADD COLUMN alert_task_id VARCHAR"))

    for table in ("audit_logs", "work_order_lifecycle_events"):
        if table not in inspector.get_table_names():
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        for column, definition in (
            ("event_hash", "VARCHAR(64)"),
            ("previous_event_hash", "VARCHAR(64)"),
            ("supersedes_event_id", "INTEGER"),
        ):
            if column not in columns:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def _ensure_app_role(connection, role: str, password: str) -> None:
    password_literal = _literal(password)
    role_exists = connection.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
    ).scalar()
    if role_exists:
        connection.execute(text(f"ALTER ROLE {role} LOGIN PASSWORD {password_literal}"))
    else:
        connection.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD {password_literal}"))


def _apply_grants(connection, app_role: str) -> None:
    tables = [table.name for table in Base.metadata.sorted_tables]
    for table in tables:
        connection.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO {app_role}"))

    connection.execute(
        text(
            "GRANT SELECT, INSERT ON TABLE audit_logs, work_order_lifecycle_events "
            f"TO {app_role}"
        )
    )
    connection.execute(
        text(
            "REVOKE UPDATE, DELETE ON TABLE audit_logs, work_order_lifecycle_events "
            f"FROM {app_role}"
        )
    )
    connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {app_role}"))
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_role}"
        )
    )
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {app_role}"
        )
    )
    # ALTER DEFAULT PRIVILEGES only covers sequences created *after* it runs, not
    # ones create_all() just made earlier in this same transaction. Grant all
    # existing sequences explicitly so every current and future autoincrement
    # table's sequence works without hardcoding table names here.
    connection.execute(text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {app_role}"))


def run_migrations() -> None:
    app_role = _identifier(os.environ.get("APP_DB_USER", "maintain_app"), "APP_DB_USER")
    app_password = os.environ.get("APP_DB_PASSWORD", "change-this-app-password")
    with engine.begin() as connection:
        Base.metadata.create_all(bind=connection)
        _ensure_legacy_columns(connection)
        _ensure_app_role(connection, app_role, app_password)
        _apply_grants(connection, app_role)
    print(f"Database migrations and grants completed for role {app_role}.")


if __name__ == "__main__":
    run_migrations()