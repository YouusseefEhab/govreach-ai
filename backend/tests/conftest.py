import json
import os
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from postgres_integration import isolated_postgres_schema, postgres_test_url

# Configure before importing app settings; never use the development database.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET"] = "isolated-test-secret"
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.providers.gemini import get_text_provider
from app.schemas.generation import TextPackage


def pytest_addoption(parser):
    parser.addoption(
        "--postgres-integration",
        action="store_true",
        help="Run the marketing integration scenarios against the dedicated PostgreSQL test database.",
    )


def pytest_configure(config):
    if config.getoption("--postgres-integration"):
        postgres_test_url()


@pytest.fixture(autouse=True)
def prevent_live_ai_calls(monkeypatch):
    from google import genai

    def blocked(*args, **kwargs):
        raise AssertionError("Live Gemini clients are forbidden in automated tests")

    monkeypatch.setattr(genai, "Client", blocked)


class FakeTextProvider:
    marketing_copy = {
        "english": {
            "headline": "Cairo Bakery's weekend pastry box",
            "slogan": "Make it a pastry weekend",
            "awareness_message": "Order an assorted pastry box from Cairo Bakery for weekend pickup.",
            "social_caption": "Planning the weekend? Pick up an assorted pastry box from Cairo Bakery.",
            "call_to_action": "Order your pastry box for pickup.",
        },
        "arabic": {
            "headline": "علبة معجنات الويك إند من كايرو بيكري",
            "slogan": "خلّي الويك إند بطعم المعجنات",
            "awareness_message": "اطلب علبة معجنات مشكلة من كايرو بيكري واستلمها في الويك إند.",
            "social_caption": "بتخطط للويك إند؟ اطلب علبة معجنات مشكلة من كايرو بيكري.",
            "call_to_action": "اطلب علبة المعجنات للاستلام.",
        },
    }

    provider_name = "fake"
    model = "test-model"

    def __init__(self):
        self.calls = []
        self.error = None
        self.result = None

    def generate(self, instructions, input_data, languages):
        inputs = json.loads(input_data)
        self.calls.append((instructions, inputs, languages))
        if self.error:
            raise self.error
        if self.result is not None:
            return self.result
        if inputs.get("campaign_type") == "marketing":
            return {language: TextPackage(**self.marketing_copy[language]) for language in languages}
        return {
            language: TextPackage(**{
                field: "اربط حزامك قبل ما تتحرك." if language == "arabic" else "Buckle up before setting off."
                for field in TextPackage.model_fields
            }) for language in languages
        }


@pytest.fixture
def provider(monkeypatch):
    fake = FakeTextProvider()
    monkeypatch.setitem(app.dependency_overrides, get_text_provider, lambda: fake)
    return fake


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        yield config, engine
    finally:
        engine.dispose()


@pytest.fixture
def postgres_migration_db(monkeypatch):
    with isolated_postgres_schema() as (url, engine):
        monkeypatch.setattr(settings, "database_url", url.render_as_string(hide_password=False))
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        yield config, engine


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
