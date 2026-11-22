"""Opt-in browser tests against a loopback copy of the real app."""

import json
import os
import re
import socket
import subprocess
from contextlib import contextmanager
from pathlib import Path
from secrets import compare_digest, token_hex
from threading import Thread

import pytest
import uvicorn
from alembic import command
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from app.core.database import get_db
from app.main import app
from app.providers.gemini import get_text_provider
from app.providers.text import GenerationError
from postgres_integration import TEST_DATABASE, TEST_URL_ENV, require_test_connection


FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or Path(path).suffix:
                raise
            return await super().get_response("index.html", scope)


@contextmanager
def serve_loopback(test_app):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(
            test_app, lifespan="off", access_log=False, log_level="warning",
            timeout_graceful_shutdown=5,
        ))
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            yield url
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("The browser test server did not shut down cleanly.")


def test_browser_workflows(request, provider, monkeypatch, tmp_path):
    if not request.config.getoption("--postgres-integration"):
        pytest.fail("Use --postgres-integration with the dedicated test database for browser tests.")
    browser_cli = FRONTEND / "node_modules" / "@playwright" / "test" / "cli.js"
    if not browser_cli.is_file():
        pytest.fail("Run npm ci in frontend to install the browser test runner.")

    config, engine = request.getfixturevalue("postgres_migration_db")
    with engine.connect() as connection:
        schema = connection.dialect.default_schema_name
        if connection.dialect.name != "postgresql" or not re.fullmatch(
            r"marketpilot_it_[0-9a-f]{32}", schema or "",
        ):
            pytest.fail("Browser tests require a dedicated PostgreSQL test schema.")
        require_test_connection(connection, schema)

    def test_db():
        with Session(engine) as session:
            require_test_connection(session.connection(), schema)
            yield session

    fake_dependency = app.dependency_overrides.get(get_text_provider)
    if fake_dependency is None or fake_dependency() is not provider or provider.provider_name != "fake":
        pytest.fail("Browser tests require the server-side fake text provider.")
    monkeypatch.setitem(app.dependency_overrides, get_db, test_db)
    original_generate = provider.generate

    def generate(instructions, input_data, languages):
        packages = original_generate(instructions, input_data, languages)
        audience = json.loads(input_data)["audience"]
        if audience == "E2E provider failure":
            raise GenerationError(503, "E2E_INTERNAL_PROVIDER_DETAIL")
        if audience == "E2E unsupported claim":
            packages["english"] = packages["english"].model_copy(update={"headline": "Save 75% today"})
        return packages

    monkeypatch.setattr(provider, "generate", generate)
    command.upgrade(config, "head")
    with engine.connect() as connection:
        revision = MigrationContext.configure(connection).get_current_revision()
        assert revision == ScriptDirectory.from_config(config).get_current_head()

    dist = tmp_path / "dist"
    env = {**os.environ, "VITE_API_BASE_URL": ""}
    env.pop(TEST_URL_ENV, None)
    subprocess.run(
        ["node", "node_modules/vite/bin/vite.js", "build", "--outDir", str(dist), "--no-emptyOutDir"],
        cwd=FRONTEND, env=env, check=True, timeout=60,
    )
    frontend = FrontendFiles(directory=dist, html=True)
    token = token_hex(16)

    async def test_app(scope, receive, send):
        path = scope.get("path", "")
        if path == "/__e2e/status" or path.startswith("/api/v1/"):
            if (
                app.dependency_overrides.get(get_text_provider) is not fake_dependency
                or app.dependency_overrides.get(get_db) is not test_db
            ):
                await JSONResponse({"detail": "Browser test isolation is unavailable"}, status_code=503)(
                    scope, receive, send,
                )
                return
            if path == "/__e2e/status":
                authorized = compare_digest(Request(scope).headers.get("x-marketpilot-e2e", ""), token)
                response = JSONResponse({
                    "database": TEST_DATABASE, "schema": schema, "revision": revision,
                    "provider": "fake", "provider_calls": len(provider.calls),
                }) if authorized else JSONResponse({"detail": "Not found"}, status_code=404)
                await response(scope, receive, send)
                return
            await app(scope, receive, send)
        else:
            await frontend(scope, receive, send)

    with serve_loopback(test_app) as url:
        subprocess.run(
            ["node", str(browser_cli), "test", "--config", "e2e/playwright.config.mjs",
             "--output", str(tmp_path / "playwright")],
            cwd=FRONTEND,
            env={**env, "MARKETPILOT_E2E_URL": url, "MARKETPILOT_E2E_TOKEN": token},
            check=True, timeout=150,
        )
