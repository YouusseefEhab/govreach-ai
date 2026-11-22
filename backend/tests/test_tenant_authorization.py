from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from threading import Event
from time import monotonic, sleep
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import AuthSession, Business, Campaign, GeneratedContent, Membership, User
from app.services import auth
from scripts.diagnostic_auth import DIAGNOSTIC_ORIGIN, seed_user, sign_in


BUSINESSES = "/api/v1/businesses"
CAMPAIGNS = "/api/v1/campaigns"
CONTENTS = "/api/v1/contents"
LEGACY = {"title": "Seat belts", "objective": "Encourage seat belt use"}
MARKETING = {
    "campaign_type": "marketing", "title": "Weekend pastries", "objective": "More pickup orders",
    "business_name": "Cairo Bakery", "offer_summary": "Pastry box", "target_audience": "Local families",
}


@pytest.fixture
def security_engine(request):
    config, engine = request.getfixturevalue(
        "postgres_migration_db" if request.config.getoption("--postgres-integration") else "migration_db"
    )
    command.upgrade(config, "head")
    return engine


@pytest.fixture
def actors(security_engine, monkeypatch):
    def test_db():
        with Session(security_engine) as db:
            yield db

    monkeypatch.setattr(settings, "auth_trusted_origin", DIAGNOSTIC_ORIGIN)
    monkeypatch.setitem(app.dependency_overrides, get_db, test_db)
    clients = {}
    user_ids = {}
    with ExitStack() as stack:
        clients["anonymous"] = stack.enter_context(TestClient(app, base_url=DIAGNOSTIC_ORIGIN))
        for role in ("owner", "editor", "viewer", "outsider"):
            email = f"{role}@example.test"
            with Session(security_engine) as db, db.begin():
                user_ids[role], password = seed_user(db, email)
            client = clients[role] = stack.enter_context(TestClient(app, base_url=DIAGNOSTIC_ORIGIN))
            sign_in(client, email, password)
            if role in {"owner", "outsider"}:
                response = client.post(BUSINESSES, json={"display_name": f"{role} shop"})
                assert response.status_code == 201
                client.headers["X-Business-ID"] = response.json()["id"]

        business_id = clients["owner"].headers["X-Business-ID"]
        with Session(security_engine) as db, db.begin():
            for role in ("editor", "viewer"):
                db.add(Membership(business_id=UUID(business_id), user_id=user_ids[role], role=role))
                clients[role].headers["X-Business-ID"] = business_id
        yield clients


def create_campaign(client, data=LEGACY):
    response = client.post(CAMPAIGNS, json=data)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def draft(client, campaign_id):
    response = client.post(f"{CAMPAIGNS}/{campaign_id}/generate-text", json={"audience": "Drivers"})
    assert response.status_code == 201, response.text
    return response.json()["contents"][0]["id"]


def operations(campaign_id, content_id):
    url = f"{CAMPAIGNS}/{campaign_id}"
    content = f"{CONTENTS}/{content_id}"
    return [
        ("GET", CAMPAIGNS, None), ("POST", CAMPAIGNS, LEGACY), ("GET", url, None),
        ("PATCH", url, {"title": "Edited"}), ("DELETE", url, None),
        ("POST", f"{url}/generate-text", {}), ("GET", f"{url}/contents", None),
        ("GET", content, None), ("PATCH", content, {"content": {"headline": "Edited"}}),
    ]


def assert_denied(response, status, detail=None):
    assert response.status_code == status, response.text
    assert response.headers["cache-control"] == "no-store"
    if detail:
        assert response.json() == {"detail": detail}


def test_every_private_operation_requires_sign_in_and_public_health_survives(actors, provider):
    anonymous = actors["anonymous"]
    business_id = actors["owner"].headers["X-Business-ID"]
    for method, url, body in operations(1, 1):
        assert_denied(anonymous.request(method, url, json=body, headers={"X-Business-ID": business_id}),
                      401, "Authentication required.")
    for method, path, body in (
        ("GET", BUSINESSES, None), ("POST", BUSINESSES, {"display_name": "Anonymous"}),
        ("GET", f"{BUSINESSES}/{business_id}", None), ("PATCH", f"{BUSINESSES}/{business_id}", {}),
    ):
        assert_denied(anonymous.request(method, path, json=body), 401, "Authentication required.")
    assert anonymous.get("/").status_code == anonymous.get("/health").status_code == 200
    assert_denied(anonymous.get(CAMPAIGNS, headers={"Origin": "https://foreign.example.test"}),
                  401, "Authentication required.")
    assert provider.calls == []


def test_selector_is_validated_and_always_requires_membership(actors, provider):
    outsider = actors["outsider"]
    outsider.headers.pop("X-Business-ID")
    assert_denied(outsider.get(CAMPAIGNS), 400)
    assert_denied(outsider.post(CAMPAIGNS, json=LEGACY, headers={"X-Business-ID": "malformed"}), 400)
    business_id = actors["owner"].headers["X-Business-ID"]
    duplicate = [("X-Business-ID", business_id), ("X-Business-ID", business_id)]
    assert_denied(outsider.get(CAMPAIGNS, headers=duplicate), 400)
    for selector in (business_id, str(uuid4())):
        headers = {"X-Business-ID": selector}
        assert_denied(outsider.get(CAMPAIGNS, headers=headers), 404, "Business not found")
        assert_denied(outsider.post(CAMPAIGNS + "/1/generate-text", json={}, headers=headers), 404, "Business not found")
    assert provider.calls == []


def test_business_membership_views_profile_permissions_and_validation(actors, security_engine):
    owner, editor, viewer, outsider = (actors[role] for role in ("owner", "editor", "viewer", "outsider"))
    business_id = owner.headers["X-Business-ID"]
    resource = f"{BUSINESSES}/{business_id}"
    profile = {"display_name": "  Cairo bakery  ", "description": "Pickup orders", "default_locale": "ar-EG",
               "website_url": "https://bakery.example.test/pickup"}
    created = owner.post(BUSINESSES, json=profile)
    assert created.status_code == 201 and created.json()["role"] == "owner"
    assert created.json()["display_name"] == "Cairo bakery"
    assert created.json()["website_url"] == profile["website_url"]
    second = owner.post(BUSINESSES, json=profile)
    assert second.status_code == 201 and second.json()["id"] != created.json()["id"]
    assert {row["id"] for row in owner.get(BUSINESSES).json()} == {business_id, created.json()["id"], second.json()["id"]}
    assert {row["id"] for row in outsider.get(BUSINESSES).json()} == {outsider.headers["X-Business-ID"]}
    for client, role in ((viewer, "viewer"), (editor, "editor")):
        assert client.get(resource).json()["role"] == role
        assert client.get(BUSINESSES).json()[0]["id"] == business_id
        assert_denied(client.patch(resource, json=profile), 403, "Permission denied")
    for url in (resource, f"{BUSINESSES}/{uuid4()}"):
        assert_denied(outsider.get(url), 404, "Business not found")
        assert_denied(outsider.patch(url, json=profile), 404, "Business not found")

    patched = owner.patch(resource, json=profile)
    assert patched.status_code == 200 and patched.json()["role"] == "owner"
    assert owner.patch(resource, json={"description": None}).json()["description"] is None
    assert owner.get(resource).json()["display_name"] == "Cairo bakery"
    for field, value in (("display_name", "   "), ("default_locale", "bad locale"),
                         ("website_url", "file:///tmp/page"), ("role", "editor"), ("id", business_id)):
        assert_denied(owner.post(BUSINESSES, json={"display_name": "Invalid", field: value}), 422)
        assert_denied(owner.patch(resource, json={field: value}), 422)
    assert_denied(owner.patch(resource, json={"display_name": None}), 422)
    with Session(security_engine) as db:
        assert db.scalar(select(func.count()).select_from(Membership)) == 6


def test_failed_first_membership_rolls_back_business(actors, security_engine):
    def reject_membership(_mapper, _connection, _target):
        raise IntegrityError("fixture insert", {}, ValueError("fixture failure"))

    owner = actors["owner"]
    before = owner.get(BUSINESSES).json()
    event.listen(Membership, "before_insert", reject_membership)
    try:
        assert_denied(owner.post(BUSINESSES, json={"display_name": "Do not save"}), 503, "Database unavailable")
    finally:
        event.remove(Membership, "before_insert", reject_membership)
    assert owner.get(BUSINESSES).json() == before
    with Session(security_engine) as db:
        assert db.scalar(select(func.count()).select_from(Business)) == 2


def test_origin_and_csrf_are_checked_before_all_writes(actors, provider):
    owner = actors["owner"]
    campaign_id = create_campaign(owner)
    content_id = draft(owner, campaign_id)
    writes = [item for item in operations(campaign_id, content_id) if item[0] != "GET"]
    writes.extend([
        ("POST", BUSINESSES, {"display_name": "Blocked"}),
        ("PATCH", f"{BUSINESSES}/{owner.headers['X-Business-ID']}", {"display_name": "Blocked"}),
    ])
    csrf = owner.headers.pop("X-CSRF-Token")
    for method, path, body in writes:
        assert_denied(owner.request(method, path, json=body), 403, "Invalid CSRF token.")
        assert_denied(owner.request(method, path, json=body, headers={"X-CSRF-Token": "0" * 64}), 403)
        assert_denied(owner.request(method, path, json=body,
                                    headers={"Origin": "https://foreign.example.test", "X-CSRF-Token": csrf}), 403)
    owner.headers["X-CSRF-Token"] = csrf
    assert len(provider.calls) == 1
    assert owner.get(f"{CAMPAIGNS}/{campaign_id}").json()["title"] == LEGACY["title"]


def test_scoped_pagination_and_hidden_resources_have_identical_errors(actors, security_engine, provider):
    owner, viewer, outsider = (actors[role] for role in ("owner", "viewer", "outsider"))
    old = create_campaign(owner)
    foreign = create_campaign(outsider, MARKETING)
    foreign_content = draft(outsider, foreign)
    latest = create_campaign(owner)
    with Session(security_engine) as db, db.begin():
        campaign = Campaign(**LEGACY)
        db.add(campaign)
        db.flush()
        historical = campaign.id
        row = GeneratedContent(
            campaign_id=historical, generation_id=uuid4(), language="english", content={"headline": "Historical"},
            provider="fake", model="fixture", prompt_version="fixture", input_snapshot={},
        )
        db.add(row)
        db.flush()
        historical_content = row.id

    assert [row["id"] for row in owner.get(CAMPAIGNS).json()] == [latest, old]
    assert [row["id"] for row in viewer.get(CAMPAIGNS, params={"skip": 1, "limit": 1}).json()] == [old]
    assert [row["id"] for row in outsider.get(CAMPAIGNS).json()] == [foreign]
    for client in (owner, viewer):
        for campaign_id, content_id in ((foreign, foreign_content), (historical, historical_content), (999999, 999999)):
            for method, resource, body in operations(campaign_id, content_id)[2:]:
                detail = "Generated content not found" if resource.startswith(CONTENTS) else "Campaign not found"
                assert_denied(client.request(method, resource, json=body), 404, detail)
            # Even a well-formed but invalid generation payload cannot disclose campaign visibility.
            assert_denied(client.post(f"{CAMPAIGNS}/{campaign_id}/generate-text", json={"audience": False}), 404)
    assert len(provider.calls) == 1
    with Session(security_engine) as db:
        assert db.get(Campaign, historical).business_id is None
        assert db.get(GeneratedContent, historical_content).campaign_id == historical


def test_roles_control_campaign_writes_draft_changes_and_review(actors, provider):
    owner, editor, viewer = (actors[role] for role in ("owner", "editor", "viewer"))
    campaign_id = create_campaign(editor, MARKETING)
    campaign_url = f"{CAMPAIGNS}/{campaign_id}"
    assert editor.patch(campaign_url, json={"title": "Edited by editor"}).status_code == 200
    generated = editor.post(f"{campaign_url}/generate-text", json={})
    assert generated.status_code == 201
    assert {row["language"] for row in generated.json()["contents"]} == {"arabic", "english"}
    content_id = generated.json()["contents"][0]["id"]
    content_url = f"{CONTENTS}/{content_id}"
    for method, resource, body in operations(campaign_id, content_id):
        response = viewer.request(method, resource, json=body)
        if method == "GET":
            assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        else:
            assert_denied(response, 403, "Permission denied")
    assert len(provider.calls) == 1
    assert_denied(editor.delete(campaign_url), 403, "Permission denied")
    for review_status in ("approved", "rejected", "draft"):
        assert_denied(editor.patch(content_url, json={"review_status": review_status}), 403, "Permission denied")
    assert_denied(editor.patch(content_url, json={"content": {"headline": "Edit"}, "review_status": "draft"}), 403)

    assert owner.patch(content_url, json={"review_status": "approved"}).json()["review_status"] == "approved"
    edited = editor.patch(content_url, json={"content": {"headline": "Revised draft"}})
    assert edited.status_code == 200 and edited.json()["review_status"] == "draft"
    assert owner.patch(content_url, json={"review_status": "rejected"}).json()["review_status"] == "rejected"
    assert owner.delete(campaign_url).status_code == 204
    assert_denied(viewer.get(content_url), 404, "Generated content not found")


def test_campaign_ownership_fields_are_rejected_on_create_and_patch(actors, security_engine):
    owner = actors["owner"]
    before = [create_campaign(owner), create_campaign(owner, MARKETING)]
    foreign = actors["outsider"].headers["X-Business-ID"]
    for field, value in (("business_id", foreign), ("businessId", None), ("membership_role", "owner"),
                         ("role", "owner"), ("ownership", {"business": foreign}), ("owner_id", foreign)):
        for data in (LEGACY, MARKETING):
            assert_denied(owner.post(CAMPAIGNS, json={**data, field: value}), 422)
        for campaign_id in before:
            assert_denied(owner.patch(f"{CAMPAIGNS}/{campaign_id}", json={"title": "Blocked", field: value}), 422)
    with Session(security_engine) as db:
        campaigns = db.scalars(select(Campaign).order_by(Campaign.id)).all()
        assert [campaign.id for campaign in campaigns] == before
        assert {str(campaign.business_id) for campaign in campaigns} == {owner.headers["X-Business-ID"]}
        assert [campaign.title for campaign in campaigns] == [LEGACY["title"], MARKETING["title"]]


@pytest.mark.parametrize(("change", "status"), [
    ("logout", 401), ("disabled", 401), ("membership", 404), ("role", 403), ("campaign", 404),
])
def test_access_changes_during_provider_execution_prevent_persistence(
    actors, security_engine, provider, monkeypatch, change, status,
):
    owner, editor = actors["owner"], actors["editor"]
    campaign_id = create_campaign(owner, MARKETING)
    provider_entered, provider_release = Event(), Event()
    original = provider.generate

    def delayed(*args):
        provider_entered.set()
        assert provider_release.wait(10), "Provider must finish after the committed access change"
        return original(*args)

    monkeypatch.setattr(provider, "generate", delayed)
    with ThreadPoolExecutor(max_workers=2) as pool:
        generation = pool.submit(editor.post, f"{CAMPAIGNS}/{campaign_id}/generate-text", json={})
        try:
            assert provider_entered.wait(5), "Generation did not reach the provider"
            if change == "logout":
                with TestClient(app, base_url=DIAGNOSTIC_ORIGIN, headers=editor.headers, cookies=editor.cookies) as other:
                    result = pool.submit(other.post, "/api/v1/auth/logout").result(timeout=5)
                    assert result.status_code == 204
            elif change == "campaign":
                assert pool.submit(owner.delete, f"{CAMPAIGNS}/{campaign_id}").result(timeout=5).status_code == 204
            else:
                def change_access():
                    with Session(security_engine) as db, db.begin():
                        user = db.scalar(select(User).where(User.email_normalized == "editor@example.test"))
                        if change == "disabled":
                            user.disabled_at = auth.utc_now()
                            return
                        membership = db.get(Membership, (UUID(editor.headers["X-Business-ID"]), user.id))
                        if change == "membership":
                            db.delete(membership)
                        else:
                            membership.role = "viewer"
                pool.submit(change_access).result(timeout=5)
        finally:
            provider_release.set()
        assert_denied(generation.result(timeout=5), status)
    assert len(provider.calls) == 1
    with Session(security_engine) as db:
        assert db.scalar(select(func.count()).select_from(GeneratedContent)) == 0


@pytest.fixture
def lock_test_engine(request):
    if not request.config.getoption("--postgres-integration"):
        pytest.skip("Requires PostgreSQL row locks")
    return request.getfixturevalue("security_engine")


@pytest.fixture
def write_clock(monkeypatch):
    clock = Mock(return_value=datetime(2030, 3, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(auth, "utc_now", clock)
    monkeypatch.setattr(settings, "auth_idle_timeout_seconds", 60)
    monkeypatch.setattr(settings, "auth_absolute_timeout_seconds", 120)
    return clock


@contextmanager
def request_blocked_on_row(engine, lock_query, start_request):
    with Session(engine) as blocker, blocker.begin():
        assert blocker.scalar(lock_query.with_for_update()) is not None
        blocker_pid = blocker.scalar(select(func.pg_backend_pid()))
        request_pid = []
        request_connected = Event()

        def observe_request(conn, _cursor, _statement, _params, _context, _many):
            pid = conn.connection.driver_connection.info.backend_pid
            if pid != blocker_pid and not request_connected.is_set():
                request_pid.append(pid)
                request_connected.set()

        event.listen(engine, "before_cursor_execute", observe_request)
        try:
            pending = start_request()
            assert request_connected.wait(8), "Request did not reach the database"
            timeout = monotonic() + 8
            while blocker_pid not in blocker.scalar(select(func.pg_blocking_pids(request_pid[0]))):
                assert not pending.done() and monotonic() < timeout, "Request never waited for the held row"
                sleep(0.01)
            assert not pending.done()
            yield pending
        finally:
            event.remove(engine, "before_cursor_execute", observe_request)


@pytest.mark.parametrize("outcome", ["idle", "absolute", "valid"])
def test_generation_rechecks_session_deadlines_after_campaign_lock_wait(
    lock_test_engine, write_clock, actors, provider, monkeypatch, outcome,
):
    owner = actors["owner"]
    campaign_id = create_campaign(owner, MARKETING)
    provider_entered, provider_release = Event(), Event()
    original_generate = provider.generate

    if outcome == "absolute":
        # Exercise the absolute deadline independently of idle expiration.
        with Session(lock_test_engine) as db, db.begin():
            owner_session = db.scalar(select(AuthSession).join(User).where(User.email == "owner@example.test"))
            owner_session.idle_expires_at += timedelta(seconds=30)
            owner_session.absolute_expires_at = write_clock.return_value + timedelta(seconds=60)

    def delayed(*args):
        assert lock_test_engine.pool.checkedout() == 0
        provider_entered.set()
        assert provider_release.wait(12), "Fake provider was never released"
        return original_generate(*args)

    monkeypatch.setattr(provider, "generate", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        generation = pool.submit(owner.post, f"{CAMPAIGNS}/{campaign_id}/generate-text", json={})

        def release_provider():
            provider_release.set()
            return generation

        try:
            assert provider_entered.wait(8), "Generation did not reach the fake provider"
            lock_query = select(Campaign.id).where(Campaign.id == campaign_id)
            with request_blocked_on_row(lock_test_engine, lock_query, release_provider):
                write_clock.return_value += timedelta(seconds=59 if outcome == "valid" else 60)
                assert not generation.done()
        finally:
            provider_release.set()
        response = generation.result(timeout=8)

    assert len(provider.calls) == 1
    with Session(lock_test_engine) as db:
        rows = db.scalars(select(GeneratedContent).where(GeneratedContent.campaign_id == campaign_id)).all()
    me = owner.get("/api/v1/auth/me")
    if outcome == "valid":
        assert (response.status_code, me.status_code) == (201, 200)
        assert len(rows) == 2 and {row.language for row in rows} == {"arabic", "english"}
        assert len({row.generation_id for row in rows}) == 1
    else:
        assert_denied(response, 401, "Authentication required.")
        assert_denied(me, 401, "Authentication required.")
        assert rows == []


@pytest.mark.parametrize("operation", [
    "campaign_create", "campaign_update", "campaign_delete", "campaign_cascade", "generation_start",
    "content_edit", "content_review", "business_create", "business_update", "session_refresh", "logout",
])
def test_writes_recheck_session_after_lock_wait(lock_test_engine, write_clock, actors, provider, operation):
    owner = actors["owner"]
    business_id = UUID(owner.headers["X-Business-ID"])
    campaign_id = create_campaign(owner)
    content_id = draft(owner, campaign_id)
    original_content = owner.get(f"{CONTENTS}/{content_id}").json()
    original_idle_deadline = write_clock.return_value + timedelta(seconds=60)

    business_lock = select(Business.id).where(Business.id == business_id)
    campaign_lock = select(Campaign.id).where(Campaign.id == campaign_id)
    content_lock = select(GeneratedContent.id).where(GeneratedContent.id == content_id)
    session_lock = select(AuthSession.id).join(User).where(User.email == "owner@example.test")
    cases = {
        "campaign_create": (business_lock, "POST", CAMPAIGNS, LEGACY),
        "campaign_update": (campaign_lock, "PATCH", f"{CAMPAIGNS}/{campaign_id}", {"title": "Changed"}),
        "campaign_delete": (campaign_lock, "DELETE", f"{CAMPAIGNS}/{campaign_id}", None),
        "campaign_cascade": (content_lock, "DELETE", f"{CAMPAIGNS}/{campaign_id}", None),
        "generation_start": (campaign_lock, "POST", f"{CAMPAIGNS}/{campaign_id}/generate-text", {"audience": "Drivers"}),
        "content_edit": (content_lock, "PATCH", f"{CONTENTS}/{content_id}", {"content": {"headline": "Changed"}}),
        "content_review": (content_lock, "PATCH", f"{CONTENTS}/{content_id}", {"review_status": "approved"}),
        "business_create": (session_lock, "POST", BUSINESSES, {"display_name": "Changed"}),
        "business_update": (business_lock, "PATCH", f"{BUSINESSES}/{business_id}", {"display_name": "Changed"}),
        "session_refresh": (session_lock, "GET", "/api/v1/auth/me", None),
        "logout": (session_lock, "POST", "/api/v1/auth/logout", None),
    }
    lock_query, method, url, body = cases[operation]
    with ThreadPoolExecutor(max_workers=1) as pool:
        def submit():
            return pool.submit(owner.request, method, url, json=body)

        with request_blocked_on_row(lock_test_engine, lock_query, submit) as pending:
            write_clock.return_value = original_idle_deadline
            assert not pending.done()
        assert_denied(pending.result(timeout=8), 401, "Authentication required.")

    assert len(provider.calls) == 1  # Only the fixture draft reached the fake provider.
    with Session(lock_test_engine) as db:
        assert db.scalar(select(func.count()).select_from(Business)) == 2
        assert db.get(Business, business_id).display_name == "owner shop"
        assert db.scalar(select(func.count()).select_from(Campaign)) == 1
        assert db.get(Campaign, campaign_id).title == LEGACY["title"]
        assert db.scalar(select(func.count()).select_from(GeneratedContent)) == 2
        assert db.get(GeneratedContent, content_id).content == original_content["content"]
        assert db.get(GeneratedContent, content_id).review_status == original_content["review_status"]
        owner_session = db.get(AuthSession, db.scalar(session_lock))
        assert owner_session.idle_expires_at == original_idle_deadline and owner_session.revoked_at is None


def test_openapi_declares_cookie_scope_csrf_and_success_contracts(actors):
    paths = actors["anonymous"].get("/openapi.json").json()["paths"]
    for method, path, _ in operations("{campaign_id}", "{content_id}"):
        operation = paths[path][method.lower()]
        assert operation["security"] == [{"MarketPilotSession": []}]
        assert {"400", "401", "403", "404"} <= set(operation["responses"])
        headers = {param["name"].lower() for param in operation["parameters"] if param["in"] == "header"}
        assert "x-business-id" in headers
        if method != "GET":
            assert {"origin", "x-csrf-token"} <= headers
    for path in (BUSINESSES, BUSINESSES + "/{business_id}"):
        for operation in paths[path].values():
            assert operation["security"] == [{"MarketPilotSession": []}]
    assert "security" not in paths["/health"]["get"]
