from datetime import datetime, timedelta, timezone
from hashlib import sha256
from unittest.mock import Mock

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import SESSION_COOKIE_NAME
from app.core.config import Settings, settings
from app.core.database import Base, get_db
from app.core.security import hash_password, password_needs_rehash, verify_password
from app.main import app
from app.models import AuthSession, User
from app.services import auth


ORIGIN = "https://auth.example.test"
AUTH = "/api/v1/auth"
EMAIL = "Pilot@example.test"
PASSWORD = "An isolated fixture password"
LOGIN_HEADERS = {"Origin": ORIGIN, "X-MarketPilot-Login": "1"}
LOGIN_BODY = {"email": EMAIL, "password": PASSWORD}


@pytest.fixture
def auth_migration_db(request):
    fixture_name = "postgres_migration_db" if request.config.getoption("--postgres-integration") else "migration_db"
    return request.getfixturevalue(fixture_name)


@pytest.fixture
def auth_engine(auth_migration_db):
    config, engine = auth_migration_db
    command.upgrade(config, "head")
    return engine


@pytest.fixture
def clock(monkeypatch):
    clock = Mock(return_value=datetime(2030, 3, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(auth, "utc_now", clock)
    monkeypatch.setattr(settings, "auth_idle_timeout_seconds", 60)
    monkeypatch.setattr(settings, "auth_absolute_timeout_seconds", 150)
    return clock


@pytest.fixture
def auth_client(auth_engine, clock, monkeypatch):
    def test_db():
        with Session(auth_engine) as db:
            yield db

    monkeypatch.setattr(settings, "auth_trusted_origin", ORIGIN)
    monkeypatch.setitem(app.dependency_overrides, get_db, test_db)
    with TestClient(app, base_url=ORIGIN) as client:
        yield client


@pytest.fixture
def user_id(auth_engine):
    with Session(auth_engine) as db, db.begin():
        user = User(email=EMAIL, email_normalized=EMAIL.casefold(), password_hash=hash_password(PASSWORD))
        db.add(user)
        db.flush()
        return user.id


def sign_in(client):
    return client.post(f"{AUTH}/login", json=LOGIN_BODY, headers=LOGIN_HEADERS)


def assert_reason(db, cookie, expected):
    with pytest.raises(auth.InvalidSession) as error:
        auth.resolve_session(db, cookie)
    assert error.value.reason == expected


def test_auth_migration_preserves_users_and_enforces_storage_constraints(auth_migration_db):
    config, engine = auth_migration_db
    command.upgrade(config, "e4d8cf106a72")
    with Session(engine) as db, db.begin():
        user = User(email=EMAIL, email_normalized=EMAIL.casefold(), password_hash=hash_password(PASSWORD))
        db.add(user)
        db.flush()
        existing_id = user.id

    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        indexes = {index["name"]: index for index in inspect(connection).get_indexes("auth_sessions")}
        assert indexes["ix_auth_sessions_token_digest"]["unique"]
        assert indexes["ix_auth_sessions_token_digest"]["column_names"] == ["token_digest"]
        assert indexes["ix_auth_sessions_user_id"]["column_names"] == ["user_id"]

    with Session(engine) as db:
        assert db.get(User, existing_id).email == EMAIL
        _, first = auth.start_session(db, EMAIL, PASSWORD)
        row = db.get(AuthSession, first.session_id)
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(AuthSession(
                user_id=existing_id, token_digest=row.token_digest, csrf_seed=row.csrf_seed,
                created_at=row.created_at, idle_expires_at=row.idle_expires_at,
                absolute_expires_at=row.absolute_expires_at,
            ))
            db.flush()
        db.delete(db.get(User, existing_id))
        db.commit()
        assert db.scalar(select(AuthSession.id)) is None


def test_password_hashes_are_salted_argon2id_and_safe_to_verify():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)
    assert first.startswith("$argon2id$") and second != first
    assert verify_password(PASSWORD, first)
    assert not password_needs_rehash(first)
    for invalid_hash in (None, "corrupt", "$argon2id$malformed"):
        assert not verify_password(PASSWORD, invalid_hash)
    assert not verify_password("different password", first)


def test_login_rehashes_a_verified_password(auth_client, auth_engine, user_id):
    prior_hash = PasswordHasher(memory_cost=8192, time_cost=2, parallelism=1).hash(PASSWORD)
    with Session(auth_engine) as db, db.begin():
        db.get(User, user_id).password_hash = prior_hash
    assert sign_in(auth_client).status_code == 200
    with Session(auth_engine) as db:
        current = db.get(User, user_id).password_hash
        assert current != prior_hash and verify_password(PASSWORD, current)
        assert not password_needs_rehash(current)


def test_login_cookie_digest_me_and_logout(auth_client, auth_engine, user_id):
    response = auth_client.post(f"{AUTH}/login", json={**LOGIN_BODY, "email": f"  {EMAIL.upper()}  "}, headers=LOGIN_HEADERS)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"user", "csrf_token"}
    assert body["user"] == {"id": str(user_id), "email": EMAIL, "email_verified_at": None}
    cookie = response.cookies[SESSION_COOKIE_NAME]
    assert cookie not in response.text
    flags = response.headers["set-cookie"].lower()
    for part in ("; httponly", "; secure", "; samesite=lax", "; path=/", "; max-age=150"):
        assert part in flags
    assert "domain=" not in flags

    with Session(auth_engine) as db:
        row = db.scalar(select(AuthSession))
        assert row.token_digest == sha256(cookie.encode("ascii")).digest()
        assert len(row.csrf_seed) == 32 and row.csrf_seed.hex() != body["csrf_token"]
        assert row.revoked_at is None

    me = auth_client.get(f"{AUTH}/me")
    assert me.status_code == 200 and me.json() == body and me.headers["cache-control"] == "no-store"
    cross_origin = auth_client.get(f"{AUTH}/me", headers={"Origin": "http://localhost:5173"})
    assert cross_origin.status_code == 403 and body["csrf_token"] not in cross_origin.text
    signed_out = auth_client.post(f"{AUTH}/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": body["csrf_token"]})
    assert signed_out.status_code == 204 and signed_out.content == b""
    assert signed_out.headers["cache-control"] == "no-store"
    clear_flags = signed_out.headers["set-cookie"].lower()
    for part in ("; httponly", "; secure", "; samesite=lax", "; path=/", "; max-age=0"):
        assert part in clear_flags
    assert "domain=" not in clear_flags
    assert auth_client.get(f"{AUTH}/me").status_code == 401
    assert auth_client.get(f"{AUTH}/me", headers={"Cookie": f"{SESSION_COOKIE_NAME}={cookie}"}).status_code == 401
    with Session(auth_engine) as db:
        assert_reason(db, cookie, auth.SessionFailure.REVOKED)


def test_credential_failures_are_generic_with_no_session_or_log_disclosure(auth_client, auth_engine, user_id, caplog):
    def attempt(email, password):
        response = auth_client.post(f"{AUTH}/login", headers=LOGIN_HEADERS, json={"email": email, "password": password})
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password."}
        assert response.headers["cache-control"] == "no-store"
        assert not response.headers.get("set-cookie")

    attempt(EMAIL, "wrong password")
    attempt("missing@example.test", PASSWORD)
    with Session(auth_engine) as db, db.begin():
        user = db.get(User, user_id)
        original_hash = user.password_hash
        user.disabled_at = auth.utc_now()
    attempt(EMAIL, PASSWORD)
    with Session(auth_engine) as db, db.begin():
        user = db.get(User, user_id)
        user.disabled_at = None
        user.password_hash = "$argon2id$broken"
    attempt(EMAIL, PASSWORD)
    with Session(auth_engine) as db:
        assert db.scalar(select(AuthSession.id)) is None
    assert PASSWORD not in caplog.text and original_hash not in caplog.text


def test_invalid_login_body_is_redacted(auth_client, caplog):
    sensitive = "test-only sensitive content"
    for data in (
        {"email": EMAIL, "password": sensitive, "extra": sensitive},
        {"email": EMAIL, "password": {"raw": sensitive}},
    ):
        response = auth_client.post(f"{AUTH}/login", json=data, headers=LOGIN_HEADERS)
        assert response.status_code == 422 and response.json() == {"detail": "Invalid authentication request."}
        assert response.headers["cache-control"] == "no-store"
    malformed = auth_client.post(f"{AUTH}/login", content='{"password": "' + sensitive,
                                 headers={**LOGIN_HEADERS, "Content-Type": "application/json"})
    assert malformed.status_code == 422 and sensitive not in malformed.text and sensitive not in caplog.text


def test_login_rejects_cross_site_bootstrap_and_insecure_transport(auth_client, auth_engine, user_id, monkeypatch):
    for headers in (
        {}, {"Origin": ORIGIN}, {"X-MarketPilot-Login": "1"},
        {**LOGIN_HEADERS, "Origin": "null"}, {**LOGIN_HEADERS, "Origin": ORIGIN + ".other.test"},
        [*LOGIN_HEADERS.items(), ("Origin", "https://other.test")],
    ):
        assert auth_client.post(f"{AUTH}/login", json=LOGIN_BODY, headers=headers).status_code == 403
    assert auth_client.post(f"{AUTH}/login", data=LOGIN_BODY, headers=LOGIN_HEADERS).status_code == 415
    over_http = auth_client.post(ORIGIN.replace("https:", "http:") + f"{AUTH}/login", json=LOGIN_BODY,
                                 headers={**LOGIN_HEADERS, "X-Forwarded-Proto": "https"})
    assert over_http.status_code == 403
    monkeypatch.setattr(settings, "auth_trusted_origin", None)
    assert sign_in(auth_client).status_code == 403
    with Session(auth_engine) as db:
        assert db.scalar(select(AuthSession.id)) is None


def test_logout_csrf_is_session_bound_and_rejects_untrusted_origins(auth_client, user_id):
    first = sign_in(auth_client)
    second = sign_in(auth_client)
    assert first.status_code == second.status_code == 200
    assert first.cookies[SESSION_COOKIE_NAME] != second.cookies[SESSION_COOKIE_NAME]
    csrf = second.json()["csrf_token"]
    for headers in (
        {"Origin": ORIGIN}, {"X-CSRF-Token": csrf}, {"Origin": "null", "X-CSRF-Token": csrf},
        {"Origin": ORIGIN, "X-CSRF-Token": first.json()["csrf_token"]},
        [("Origin", ORIGIN), ("X-CSRF-Token", csrf), ("X-CSRF-Token", csrf)],
        [("Origin", ORIGIN), ("Origin", "https://other.test"), ("X-CSRF-Token", csrf)],
    ):
        response = auth_client.post(f"{AUTH}/logout", headers=headers)
        assert response.status_code == 403 and csrf not in response.text
        assert "set-cookie" not in response.headers
    assert auth_client.post(f"{AUTH}/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}).status_code == 204
    first_cookie = first.cookies[SESSION_COOKIE_NAME]
    assert auth_client.get(f"{AUTH}/me", headers={"Cookie": f"{SESSION_COOKIE_NAME}={first_cookie}"}).status_code == 200


def test_missing_malformed_and_unknown_cookies_are_safe(auth_client, auth_engine):
    for token, reason in ((None, auth.SessionFailure.MISSING), ("invalid token", auth.SessionFailure.MALFORMED),
                          ("a" * 43, auth.SessionFailure.UNKNOWN)):
        headers = {} if token is None else {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}
        response = auth_client.get(f"{AUTH}/me", headers=headers)
        assert response.status_code == 401 and response.json() == {"detail": "Authentication required."}
        with Session(auth_engine) as db:
            assert_reason(db, token, reason)


def test_idle_expiry_is_enforced_at_deadline(auth_client, auth_engine, user_id, clock):
    response = sign_in(auth_client)
    assert response.status_code == 200
    clock.return_value += timedelta(seconds=60)
    assert auth_client.get(f"{AUTH}/me").status_code == 401
    with Session(auth_engine) as db:
        assert_reason(db, response.cookies[SESSION_COOKIE_NAME], auth.SessionFailure.EXPIRED)


def test_activity_renews_idle_but_cannot_extend_absolute_expiry(auth_client, user_id, clock):
    assert sign_in(auth_client).status_code == 200
    for advance in (50, 50, 49):
        clock.return_value += timedelta(seconds=advance)
        assert auth_client.get(f"{AUTH}/me").status_code == 200
    clock.return_value += timedelta(seconds=1)
    assert auth_client.get(f"{AUTH}/me").status_code == 401


def test_disabling_a_user_invalidates_an_existing_session(auth_client, auth_engine, user_id):
    response = sign_in(auth_client)
    assert response.status_code == 200
    with Session(auth_engine) as db, db.begin():
        db.get(User, user_id).disabled_at = auth.utc_now()
    assert auth_client.get(f"{AUTH}/me").status_code == 401
    with Session(auth_engine) as db:
        assert_reason(db, response.cookies[SESSION_COOKIE_NAME], auth.SessionFailure.DISABLED)


def test_validated_request_cannot_refresh_a_concurrently_revoked_session(auth_client, auth_engine, user_id, clock):
    response = sign_in(auth_client)
    cookie = response.cookies[SESSION_COOKIE_NAME]
    with Session(auth_engine) as stale_db, Session(auth_engine) as logout_db:
        snapshot = auth.resolve_session(stale_db, cookie)
        logout = auth.resolve_session(logout_db, cookie)
        auth.revoke_session(logout_db, logout)
        clock.return_value += timedelta(seconds=30)
        with pytest.raises(auth.InvalidSession) as error:
            auth.refresh_session(stale_db, snapshot)
        assert error.value.reason == auth.SessionFailure.CHANGED
        assert_reason(stale_db, cookie, auth.SessionFailure.REVOKED)
    assert auth_client.get(f"{AUTH}/me").status_code == 401


def test_login_rechecks_the_password_before_creating_the_session(auth_client, auth_engine, user_id, monkeypatch):
    def change_password_after_verify(password, stored_hash):
        verified = verify_password(password, stored_hash)
        with Session(auth_engine) as db, db.begin():
            db.get(User, user_id).password_hash = hash_password("replacement fixture password")
        return verified

    monkeypatch.setattr(auth, "verify_password", change_password_after_verify)
    assert sign_in(auth_client).status_code == 401
    with Session(auth_engine) as db:
        assert db.scalar(select(AuthSession.id)) is None


def test_auth_openapi_is_scoped_to_the_new_routes(auth_client):
    schema = auth_client.get("/openapi.json").json()
    paths = schema["paths"]
    assert {path for path in paths if path.startswith(AUTH)} == {f"{AUTH}/{name}" for name in ("login", "me", "logout")}
    assert schema["components"]["securitySchemes"]["MarketPilotSession"] == {
        "type": "apiKey", "in": "cookie", "name": SESSION_COOKIE_NAME,
    }
    assert paths[f"{AUTH}/me"]["get"]["security"] == [{"MarketPilotSession": []}]
    assert paths[f"{AUTH}/logout"]["post"]["security"] == [{"MarketPilotSession": []}]
    assert "security" not in paths["/api/v1/campaigns"]["get"]
    assert "password_hash" not in schema["components"]["schemas"]["UserRead"]["properties"]


@pytest.mark.parametrize("invalid", ["http://localhost:5173", "null", "*", ORIGIN + "/", ORIGIN + "?query"])
def test_settings_accept_only_an_exact_https_auth_origin(invalid, monkeypatch):
    monkeypatch.delenv("AUTH_TRUSTED_ORIGIN", raising=False)
    assert Settings(_env_file=None).auth_trusted_origin is None
    assert Settings(_env_file=None, auth_trusted_origin=ORIGIN).auth_trusted_origin == ORIGIN
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_trusted_origin=invalid)
