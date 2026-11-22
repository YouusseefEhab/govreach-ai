"""Authenticate in-process clients against isolated or rollback-only diagnostic data."""

from contextlib import contextmanager
from secrets import token_urlsafe
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models import User


DIAGNOSTIC_ORIGIN = "https://marketpilot-diagnostic.test"


def seed_user(db, email):
    password = token_urlsafe(32)
    user = User(email=email, email_normalized=email.casefold(), password_hash=hash_password(password))
    db.add(user)
    db.flush()
    return user.id, password


def sign_in(client, email, password):
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password},
        headers={"Origin": DIAGNOSTIC_ORIGIN, "X-MarketPilot-Login": "1"},
    )
    assert response.status_code == 200, "Diagnostic login failed"
    client.headers.update({"Origin": DIAGNOSTIC_ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]})


@contextmanager
def owner_client(session_factory):
    previous_origin = settings.auth_trusted_origin
    settings.auth_trusted_origin = DIAGNOSTIC_ORIGIN
    try:
        email = f"diagnostic-{uuid4().hex}@example.test"
        with session_factory() as db, db.begin():
            _, password = seed_user(db, email)
        with TestClient(app, base_url=DIAGNOSTIC_ORIGIN) as client:
            sign_in(client, email, password)
            response = client.post("/api/v1/businesses", json={"display_name": "Isolated test business"})
            assert response.status_code == 201, "Diagnostic business creation failed"
            client.headers["X-Business-ID"] = response.json()["id"]
            yield client
    finally:
        settings.auth_trusted_origin = previous_origin
