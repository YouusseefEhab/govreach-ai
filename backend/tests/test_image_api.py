import os
import time

import pytest
from sqlalchemy import select

from app.api.v1.images import image_provider
from app.main import app
from app.models.image_generation import ImageGeneration
from app.providers.image import ImageProviderError
from app.services import campaign as campaign_service
from app.services.image_library import get_image_storage
from app.services.image_maintenance import reconcile
from app.storage.images import ImageStorageError, LocalImageStorage
from tests.test_image_foundation import approved_source
from tests.test_image_pipeline import CountingProvider


@pytest.fixture
def image_api(client, db, tmp_path, monkeypatch):
    campaign, source, sibling = approved_source(db)
    storage = LocalImageStorage(tmp_path)
    provider = CountingProvider()
    app.dependency_overrides[get_image_storage] = lambda: storage
    app.dependency_overrides[image_provider] = lambda: provider
    monkeypatch.setattr(campaign_service, "get_image_storage", lambda: storage)
    body = {"source_content_id": source.id, "visual_brief": "A safely parked car, no text"}
    url = f"/api/v1/campaigns/{campaign.id}/generate-image"
    return client, db, campaign, source, sibling, storage, provider, body, url


def create(api, key="api_test_1"):
    return api[0].post(api[-1], json=api[-2], headers={"Idempotency-Key": key})


def test_image_api_lifecycle_replay_review_file_and_cascade(image_api):
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    response = create(image_api)
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["request_state"] == "ready" and row["review_status"] == "draft"
    assert row["source_is_current"] and row["provider"] == "fake"
    assert "storage_key" not in row and "checksum" not in row
    image_url = f"/api/v1/images/{row['id']}"
    assert create(image_api).status_code == 200 and provider.calls == 1
    assert client.get(image_url).json() == row
    assert client.get(f"/api/v1/campaigns/{campaign.id}/images").json() == [row]
    assert client.get(f"/api/v1/campaigns/{campaign.id}/images?skip=1&limit=1").json() == []
    preview = client.get(image_url + "/file")
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert preview.headers["content-disposition"].startswith("inline;")
    assert client.get(image_url + "/file?download=true").headers["content-disposition"].startswith("attachment;")
    assert client.patch(image_url, json={"review_status": "approved"}).json()["review_status"] == "approved"
    assert client.get(f"/api/v1/contents/{sibling.id}").json()["review_status"] == "draft"
    assert client.patch(image_url, json={"review_status": "rejected"}).json()["review_status"] == "rejected"
    assert client.delete(f"/api/v1/campaigns/{campaign.id}").status_code == 204
    assert client.get(image_url).status_code == 404
    assert list(storage.root.iterdir()) == []


def test_stale_source_blocks_approval_but_preserves_history_and_file(image_api):
    client, db, campaign, source, _, storage, provider, body, url = image_api
    row = create(image_api).json()
    image_url = f"/api/v1/images/{row['id']}"
    client.patch(f"/api/v1/contents/{source.id}", json={"content": {"headline": "Changed headline"}})
    assert client.get(image_url).json()["source_is_current"] is False
    assert client.patch(image_url, json={"review_status": "approved"}).status_code == 409
    assert client.patch(image_url, json={"review_status": "rejected"}).status_code == 200
    assert client.get(image_url + "/file").status_code == 200
    assert create(image_api).status_code == 200 and provider.calls == 1


@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": "bad/key"}, {"Idempotency-Key": "x" * 129}])
def test_request_identity_validation(image_api, headers):
    assert image_api[0].post(image_api[-1], json=image_api[-2], headers=headers).status_code == 422
    assert image_api[6].calls == 0


def test_conflicts_and_source_gates(image_api):
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    assert client.post(url, json={**body, "source_content_id": sibling.id}, headers={"Idempotency-Key": "draft"}).status_code == 409
    assert create(image_api).status_code == 201
    assert client.post(url, json={**body, "visual_brief": "Another scene"}, headers={"Idempotency-Key": "api_test_1"}).status_code == 409
    for query in ["skip=-1", "limit=101", "limit=0"]:
        assert client.get(f"/api/v1/campaigns/{campaign.id}/images?{query}").status_code == 422
    assert client.get("/api/v1/campaigns/99999/images").status_code == 404
    assert client.get("/api/v1/images/99999").status_code == 404
    assert client.get("/api/v1/images/99999/file").status_code == 404
    assert client.patch("/api/v1/images/99999", json={"review_status": "approved"}).status_code == 404
    assert client.patch(f"/api/v1/images/{create(image_api).json()['id']}", json={"review_status": "approved", "visual_brief": "changed"}).status_code == 422


@pytest.mark.parametrize("failure,state,status", [(TimeoutError(), "outcome_unknown", 504),
    (ImageProviderError("quota", 503, "Quota unavailable"), "failed", 503)])
def test_failed_requests_are_inspectable_and_replay_does_not_retry(image_api, failure, state, status):
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    def fail(*args):
        raise failure
    provider.callback = fail
    assert create(image_api).status_code == status
    replay = create(image_api)
    assert replay.status_code == 200 and replay.json()["request_state"] == state
    assert provider.calls == 1
    image_url = f"/api/v1/images/{replay.json()['id']}"
    assert client.get(image_url + "/file").status_code == 409
    assert client.patch(image_url, json={"review_status": "approved"}).status_code == 409


@pytest.mark.parametrize("damage", ["missing", "corrupted"])
def test_missing_or_corrupt_file_cannot_be_served_or_approved(image_api, damage):
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    row = create(image_api).json()
    key = db.get(ImageGeneration, row["id"]).storage_key
    if damage == "missing":
        storage.delete(key)
    else:
        (storage.root / key).write_bytes(b"unsafe bytes")
    image_url = f"/api/v1/images/{row['id']}"
    assert client.get(image_url + "/file").status_code == 503
    assert client.patch(image_url, json={"review_status": "approved"}).status_code == 503
    assert client.get(image_url).json()["review_status"] == "draft"


def test_failed_delete_cleanup_leaves_reconcilable_orphan(image_api, monkeypatch):
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    row = create(image_api).json()
    path = storage.root / db.get(ImageGeneration, row["id"]).storage_key
    def fail(key):
        raise ImageStorageError("unavailable")
    monkeypatch.setattr(storage, "delete", fail)
    assert client.delete(f"/api/v1/campaigns/{campaign.id}").status_code == 204
    assert path.exists() and db.scalar(select(ImageGeneration.id)) is None


def test_reconciliation_protects_references_young_files_and_requires_offline(image_api):
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    create(image_api)
    orphan = storage.put(b"orphan", "image/png")
    young = storage.put(b"young", "image/png")
    old = time.time() - 48 * 3600
    os.utime(storage.root / orphan.key, (old, old))
    for path in storage.root.iterdir():
        if path.name not in {orphan.key, young.key}:
            os.utime(path, (old, old))
    report = reconcile(db, storage)
    assert report["orphans"] == [orphan.key] and report["removed"] == []
    with pytest.raises(ValueError, match="offline"):
        reconcile(db, storage, apply=True)
    report = reconcile(db, storage, apply=True, offline=True)
    assert report["removed"] == [orphan.key]
    assert (storage.root / young.key).exists()
    assert client.get(f"/api/v1/campaigns/{campaign.id}/images").json()[0]["request_state"] == "ready"


def test_recovery_never_retries_and_only_marks_old_generating_request(image_api):
    from datetime import datetime, timedelta, timezone
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    def fail(*args):
        raise TimeoutError()
    provider.callback = fail
    create(image_api)
    row = db.scalar(select(ImageGeneration))
    row.request_state = "generating"
    row.updated_at = datetime.now(timezone.utc) - timedelta(hours=48)
    db.commit()
    with pytest.raises(ValueError):
        reconcile(db, storage, mark_unknown_id=row.id)
    assert reconcile(db, storage, offline=True, mark_unknown_id=row.id)["marked_unknown"] == [row.id]
    assert create(image_api).json()["request_state"] == "outcome_unknown"
    assert provider.calls == 1


@pytest.mark.parametrize("state", ["reserved", "generating"])
def test_pending_replay_is_metadata_only_and_young_recovery_is_ignored(image_api, state):
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    row_id = create(image_api).json()["id"]
    row = db.get(ImageGeneration, row_id)
    row.request_state = state
    db.commit()
    response = create(image_api)
    assert response.status_code == 200 and response.json()["request_state"] == state
    assert provider.calls == 1
    assert reconcile(db, storage, offline=True, mark_unknown_id=row_id)["marked_unknown"] == []


def test_failed_campaign_commit_does_not_delete_image_bytes(image_api, monkeypatch):
    from sqlalchemy.exc import OperationalError
    client, db, campaign, source, sibling, storage, provider, body, url = image_api
    row_id = create(image_api).json()["id"]
    key = db.get(ImageGeneration, row_id).storage_key
    def fail():
        raise OperationalError("commit", {}, Exception("connection failed"))
    monkeypatch.setattr(db, "commit", fail)
    with pytest.raises(OperationalError):
        campaign_service.delete_campaign(db, campaign.id)
    db.rollback()
    assert storage.read(key) and db.get(ImageGeneration, row_id) is not None
