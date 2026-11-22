from unittest.mock import Mock

import pytest

from postgres_integration import TEST_DATABASE, TEST_URL_ENV, postgres_test_url, require_test_connection


@pytest.mark.parametrize("configured", [None, "", "  "])
def test_postgres_mode_requires_its_own_url(monkeypatch, configured):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://dev@127.0.0.1:5432/govreach")
    if configured is None:
        monkeypatch.delenv(TEST_URL_ENV, raising=False)
    else:
        monkeypatch.setenv(TEST_URL_ENV, configured)
    with pytest.raises(pytest.UsageError, match=f"Set {TEST_URL_ENV}"):
        postgres_test_url()


@pytest.mark.parametrize("database", ["govreach", "postgres", "template0", "template1", "other_test"])
def test_postgres_mode_refuses_other_databases(monkeypatch, database):
    url = f"postgresql+psycopg://test:synthetic-password@127.0.0.1:5432/{database}"
    monkeypatch.setenv(TEST_URL_ENV, url)
    with pytest.raises(pytest.UsageError, match=TEST_DATABASE) as error:
        postgres_test_url()
    assert "synthetic-password" not in str(error.value)


@pytest.mark.parametrize("url", [
    "not-a-url",
    "sqlite:///:memory:",
    "postgresql://test@127.0.0.1:5432/marketpilot_integration_test",
    "postgresql+psycopg://test@remote.example:5432/marketpilot_integration_test",
    "postgresql+psycopg://test@127.0.0.1/marketpilot_integration_test",
    "postgresql+psycopg://test@127.0.0.1:bad/marketpilot_integration_test",
    "postgresql+psycopg://test@127.0.0.1:5432/marketpilot_integration_test?dbname=govreach",
    "postgresql+psycopg://test@127.0.0.1:5432/marketpilot_integration_test?options=-csearch_path%3Dpublic",
])
def test_postgres_mode_refuses_malformed_or_redirecting_urls(monkeypatch, url):
    monkeypatch.setenv(TEST_URL_ENV, url)
    with pytest.raises(pytest.UsageError, match=TEST_URL_ENV):
        postgres_test_url()


def test_postgres_mode_parses_explicit_local_test_url(monkeypatch):
    monkeypatch.setenv(
        TEST_URL_ENV, "postgresql+psycopg://test:dummy%40value@127.0.0.1:5432/marketpilot_integration_test",
    )
    url = postgres_test_url()
    assert (url.database, url.host, url.port, url.username) == (TEST_DATABASE, "127.0.0.1", 5432, "test")
    assert url.password == "dummy@value"


@pytest.mark.parametrize(("database", "schema"), [
    ("govreach", "marketpilot_it_example"),
    (TEST_DATABASE, "public"),
])
def test_postgres_mode_checks_server_identity_before_schema_operations(database, schema):
    connection = Mock()
    connection.execute.return_value.one.return_value = (database, schema)
    with pytest.raises(pytest.UsageError, match="expected test database and schema"):
        require_test_connection(connection, "marketpilot_it_example")
