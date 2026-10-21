import base64
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models.campaign import Campaign
from app.models.generated_content import GeneratedContent
from app.models.image_generation import ImageGeneration
from app.repositories import campaign as campaigns
from app.repositories import generated_content as contents
from app.repositories import image_generation as images
from app.schemas.campaign import CampaignCreate
from app.schemas.generation import ContentUpdate, TextGenerationRequest, TextPackage
from app.schemas.image_generation import ImageGenerationRequest, ImageRequestIdentity
from app.services.image_generation import ImageRequestError, reserve_image_request, source_is_current
from app.storage.images import ImageStorageError, LocalImageStorage


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jfZkAAAAASUVORK5CYII=')


def approved_source(db):
    campaign = campaigns.create_campaign(db, CampaignCreate(title="Seat belts", objective="Buckle up"))
    rows = contents.save_text_generation(
        db, campaign, TextGenerationRequest(audience="Drivers"),
        {language: TextPackage(**{field: "Test message" for field in TextPackage.model_fields}) for language in ["arabic", "english"]},
        provider="fake", model="fake-text", prompt_version="test", source_references=[{"title": "Supplied source"}],
    )
    source = contents.update_content(db, rows[0], ContentUpdate(review_status="approved"))
    return campaign, source, rows[1]


def reserve(db, campaign, source, key="request_1", brief="A parked car with seat belts"):
    return reserve_image_request(db, campaign.id, ImageGenerationRequest(source_content_id=source.id, visual_brief=brief), ImageRequestIdentity(key=key))


def test_reservation_is_durable_and_same_key_never_creates_a_second_request(db):
    campaign, source, _ = approved_source(db)
    row, created = reserve(db, campaign, source)
    assert created and row.request_state == "reserved"
    assert row.review_status == "draft" and row.storage_key is None
    assert row.provider == "fake"
    row_id = row.id
    db.expire_all()
    replay, created = reserve(db, campaign, source)
    assert not created and replay.id == row_id
    assert len(list(db.scalars(select(ImageGeneration)))) == 1
    with pytest.raises(ImageRequestError) as error:
        reserve(db, campaign, source, brief="Different scene")
    assert error.value.status_code == 409


def test_source_gate_and_wrong_campaign_are_checked_before_reserving(db):
    campaign, source, sibling = approved_source(db)
    with pytest.raises(ImageRequestError) as error:
        reserve(db, campaign, sibling)
    assert error.value.status_code == 409
    other = campaigns.create_campaign(db, CampaignCreate(title="Other", objective="Other"))
    with pytest.raises(ImageRequestError) as error:
        reserve(db, other, source)
    assert error.value.status_code == 404
    campaign.domain = "other"
    db.commit()
    with pytest.raises(ImageRequestError) as error:
        reserve(db, campaign, source)
    assert error.value.status_code == 409
    assert list(db.scalars(select(ImageGeneration))) == []


def test_snapshot_survives_edits_and_becomes_ineligible_without_touching_other_language(db):
    campaign, source, sibling = approved_source(db)
    row, _ = reserve(db, campaign, source)
    assert source_is_current(db, row)
    contents.update_content(db, source, ContentUpdate(content={"headline": "Edited headline"}))
    assert not source_is_current(db, row)
    contents.update_content(db, source, ContentUpdate(review_status="approved"))
    assert not source_is_current(db, row)
    db.refresh(row)
    assert row.source_snapshot["content"]["headline"] == "Test message"
    assert row.source_references == [{"title": "Supplied source"}]
    assert sibling.content["headline"] == "Test message"
    assert sibling.review_status == "draft"
    replay, created = reserve(db, campaign, source)
    assert not created and replay.id == row.id


def test_only_one_caller_claims_request_and_unknown_outcome_is_never_reclaimed(db):
    campaign, source, _ = approved_source(db)
    row, _ = reserve(db, campaign, source)
    assert images.claim_reserved(db, row.id)
    assert not images.claim_reserved(db, row.id)
    assert images.mark_outcome_unknown(db, row.id)
    assert not images.mark_outcome_unknown(db, row.id)
    assert not images.claim_reserved(db, row.id)
    replay, created = reserve(db, campaign, source)
    assert not created and replay.request_state == "outcome_unknown"


def test_unique_request_identity_is_enforced_by_database(db):
    campaign, source, _ = approved_source(db)
    row, _ = reserve(db, campaign, source)
    fields = {column.name: getattr(row, column.name) for column in ImageGeneration.__table__.columns if column.name != "id"}
    db.add(ImageGeneration(**fields))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_source_deletion_cascades_only_its_image_metadata(db):
    campaign, source, sibling = approved_source(db)
    reserve(db, campaign, source)
    db.execute(delete(GeneratedContent).where(GeneratedContent.id == source.id))
    db.commit()
    assert list(db.scalars(select(ImageGeneration))) == []
    assert db.get(GeneratedContent, sibling.id)


@pytest.mark.parametrize("change", [{"request_state": "invalid"}, {"review_status": "approved"}, {"request_state": "ready"}])
def test_database_rejects_invalid_lifecycle_or_ready_record_without_file(db, change):
    campaign, source, _ = approved_source(db)
    row, _ = reserve(db, campaign, source)
    for field, value in change.items():
        setattr(row, field, value)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_campaign_cascade_removes_metadata_but_preserves_unrelated_text(db):
    campaign, source, _ = approved_source(db)
    reserve(db, campaign, source)
    other, other_source, _ = approved_source(db)
    other_row, _ = reserve(db, other, other_source)
    other_id = other_row.id
    db.execute(delete(Campaign).where(Campaign.id == campaign.id))
    db.commit()
    assert [row.id for row in db.scalars(select(ImageGeneration))] == [other_id]
    assert db.get(GeneratedContent, other_source.id)


@pytest.mark.parametrize("key", ["", "   ", "../path", "a" * 129])
def test_invalid_request_identity_is_rejected(key):
    with pytest.raises(ValidationError):
        ImageRequestIdentity(key=key)


@pytest.mark.parametrize("changes", [{"visual_brief": " "}, {"source_content_id": 0}, {"style": "unsupported"}, {"count": 20}])
def test_invalid_image_brief_is_rejected(changes):
    with pytest.raises(ValidationError):
        ImageGenerationRequest(**{"source_content_id": 1, "visual_brief": "Scene", **changes})


def test_local_storage_roundtrip_unique_keys_checksum_and_idempotent_delete(tmp_path):
    root = tmp_path / "media"
    store = LocalImageStorage(root)
    assert not root.exists()  # Construction/import does not create directories.
    first = store.put(PNG, "image/png")
    second = store.put(PNG, "image/png")
    assert first.key != second.key
    assert first.checksum == second.checksum and first.byte_count == len(PNG)
    assert store.read(first.key) == PNG
    assert store.delete(first.key)
    assert not store.delete(first.key)
    assert store.read(second.key) == PNG
    with pytest.raises(ImageStorageError):
        store.read(first.key)


@pytest.mark.parametrize("key", ["../secret.png", "C:/secret.png", "/etc/passwd", "plain.png", "a" * 32 + ".svg"])
def test_local_storage_rejects_untrusted_paths_for_all_operations(tmp_path, key):
    store = LocalImageStorage(tmp_path)
    for operation in [store.read, store.delete]:
        with pytest.raises(ImageStorageError):
            operation(key)


def test_storage_rejects_bad_size_type_oversized_reads_and_safe_write_failure(tmp_path, monkeypatch):
    store = LocalImageStorage(tmp_path, max_bytes=100)
    for data, mime in [(b"", "image/png"), (b"x" * 101, "image/png"), (PNG, "image/svg+xml")]:
        with pytest.raises(ImageStorageError):
            store.put(data, mime)
    key = uuid4().hex + ".png"
    (tmp_path / key).write_bytes(b"x" * 101)
    with pytest.raises(ImageStorageError):
        store.read(key)
    def denied(*args, **kwargs):
        raise PermissionError("Private path must not escape in exception")
    monkeypatch.setattr(Path, "mkdir", denied)
    with pytest.raises(ImageStorageError, match="Image storage write failed"):
        store.put(PNG, "image/png")
