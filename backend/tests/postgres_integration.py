"""Connection and schema isolation for the opt-in PostgreSQL tests."""

import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.schema import CreateSchema, DropSchema


TEST_DATABASE = "marketpilot_integration_test"
TEST_URL_ENV = "MARKETPILOT_TEST_DATABASE_URL"


def postgres_test_url():
    configured = os.environ.get(TEST_URL_ENV)
    if not configured or not configured.strip():
        raise pytest.UsageError(f"Set {TEST_URL_ENV} before using --postgres-integration.")
    try:
        url = make_url(configured)
    except (ArgumentError, ValueError):
        raise pytest.UsageError(f"{TEST_URL_ENV} is not a valid SQLAlchemy URL.") from None
    if (
        url.drivername != "postgresql+psycopg"
        or url.database != TEST_DATABASE
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not url.username
        or not url.port
        or not 1 <= url.port <= 65535
        or url.query
    ):
        raise pytest.UsageError(
            f"{TEST_URL_ENV} must use postgresql+psycopg, a local host, "
            f"an explicit user and port, and database {TEST_DATABASE}, without query parameters."
        )
    return url


def require_test_connection(connection, schema=None):
    database, current_schema = connection.execute(
        text("SELECT current_database(), current_schema()")
    ).one()
    if database != TEST_DATABASE or (schema is not None and current_schema != schema):
        raise pytest.UsageError("PostgreSQL connection did not resolve to the expected test database and schema.")


@contextmanager
def isolated_postgres_schema():
    url = postgres_test_url()
    admin_engine = create_engine(url, hide_parameters=True)
    schema = f"marketpilot_it_{uuid4().hex}"
    try:
        with admin_engine.begin() as connection:
            require_test_connection(connection)
            connection.execute(CreateSchema(schema))
        try:
            # Alembic opens its own connections from this same schema-scoped URL.
            scoped_url = url.set(query={"options": f"-csearch_path={schema}"})
            engine = create_engine(scoped_url, hide_parameters=True)
            try:
                with engine.connect() as connection:
                    require_test_connection(connection, schema)
                yield scoped_url, engine
            finally:
                engine.dispose()
        finally:
            with admin_engine.begin() as connection:
                require_test_connection(connection)
                connection.execute(DropSchema(schema, cascade=True))
    finally:
        admin_engine.dispose()
