import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Configure before importing app settings; never use the development database.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET"] = "isolated-test-secret"
os.environ["GEMINI_API_KEY"] = ""

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def prevent_live_ai_calls(monkeypatch):
    from google import genai

    def blocked(*args, **kwargs):
        raise AssertionError("Live Gemini clients are forbidden in automated tests")

    monkeypatch.setattr(genai, "Client", blocked)


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        # SQLite defaults to ignoring foreign keys; exercise PostgreSQL semantics.
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(test_engine):
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine):

    def test_db():
        with Session(test_engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = test_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
