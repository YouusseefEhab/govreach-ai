from io import BytesIO

from PIL import Image
import pytest
from sqlalchemy.exc import OperationalError

from app.models.image_generation import ImageGeneration
from app.providers.image import FakeImageProvider, ImageOutput, ImageProviderError
from app.repositories import generated_content as contents
from app.repositories import image_generation as repository
from app.schemas.generation import ContentUpdate
from app.schemas.image_generation import ImageGenerationRequest, ImageRequestIdentity
from app.services.image_generation import ImageRequestError, generate_image
from app.services.image_validation import InvalidImageError, validate_image
from app.storage.images import ImageStorageError, LocalImageStorage
from tests.test_image_foundation import approved_source


def encoded(fmt="PNG", size=(32, 32)):
    buffer = BytesIO()
    with Image.new("RGB", size, color="blue") as image:
        image.save(buffer, format=fmt)
    return buffer.getvalue()


class CountingProvider(FakeImageProvider):
    def __init__(self, callback=None):
        self.calls = 0
        self.callback = callback

    def generate(self, brief, snapshot, style):
        self.calls += 1
        if self.callback:
            return self.callback(brief, snapshot, style)
        return super().generate(brief, snapshot, style)


def arguments(db, tmp_path):
    campaign, source, sibling = approved_source(db)
    request = ImageGenerationRequest(source_content_id=source.id, visual_brief="Parked car, correct seat belts, no text")
    return campaign, source, sibling, request, ImageRequestIdentity(key="pipeline_1"), LocalImageStorage(tmp_path)


@pytest.mark.parametrize("fmt,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg")])
def test_decoder_accepts_verified_single_frame_images(fmt, mime):
    output = ImageOutput(encoded(fmt), mime)
    verified = validate_image(output)
    assert (verified.width, verified.height, verified.mime_type) == (32, 32, mime)
    assert verified.data == output.data


@pytest.mark.parametrize("output", [
    ImageOutput(b"", "image/png"), ImageOutput(b"<svg></svg>", "image/png"),
    ImageOutput(b"<html></html>", "image/jpeg"), ImageOutput(encoded(), "image/jpeg"),
    ImageOutput(encoded(size=(32, 20)), "image/png"),
    ImageOutput(encoded()[:30], "image/png"), ImageOutput(b"data", "image/svg+xml"),
    ImageOutput("not bytes", "image/png"), ImageOutput(b"data", {}), [],
])
def test_decoder_rejects_malformed_mismatched_non_square_or_active_formats(output):
    with pytest.raises(InvalidImageError):
        validate_image(output)


def test_decoder_enforces_byte_and_pixel_limits_before_full_decode():
    output = ImageOutput(encoded(), "image/png")
    for limits in [{"max_bytes": 1}, {"max_edge": 16}, {"max_pixels": 100}]:
        with pytest.raises(InvalidImageError):
            validate_image(output, **limits)


def test_decoder_rejects_animation():
    buffer = BytesIO()
    with Image.new("RGB", (32, 32), "red") as first, Image.new("RGB", (32, 32), "blue") as second:
        first.save(buffer, format="PNG", save_all=True, append_images=[second], duration=10, loop=0)
    with pytest.raises(InvalidImageError, match="Animated"):
        validate_image(ImageOutput(buffer.getvalue(), "image/png"))


def test_pipeline_saves_verified_draft_without_db_transaction_during_provider_and_replays(db, tmp_path):
    campaign, _, sibling, request, identity, storage = arguments(db, tmp_path)
    def output(brief, snapshot, style):
        assert not db.in_transaction()
        assert brief == request.visual_brief and style == "illustration"
        assert snapshot["review_status"] == "approved"
        return ImageOutput(encoded(), "image/png")
    provider = CountingProvider(output)
    row, created = generate_image(db, campaign.id, request, identity, provider, storage)
    assert created and row.request_state == "ready" and row.review_status == "draft"
    assert row.width == row.height == 32
    assert validate_image(ImageOutput(storage.read(row.storage_key), row.mime_type)).width == 32
    row_id = row.id
    db.expire_all()
    replay, created = generate_image(db, campaign.id, request, identity, provider, storage)
    assert not created and replay.id == row_id and provider.calls == 1
    assert len(list(tmp_path.iterdir())) == 1
    assert sibling.review_status == "draft"


@pytest.mark.parametrize("failure,state,status", [
    (TimeoutError("private timeout details"), "outcome_unknown", 504),
    (RuntimeError("private provider body"), "outcome_unknown", 503),
    (ImageProviderError("policy_blocked", 422, "Image was blocked by provider policy"), "failed", 422),
    (ImageProviderError("unavailable", 503, "Image service unavailable"), "failed", 503),
    (ImageProviderError("connection_lost", 503, "Check saved request", ambiguous=True), "outcome_unknown", 503),
])
def test_provider_failures_are_persisted_safe_and_never_replayed(db, tmp_path, failure, state, status):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    def fail(*args):
        raise failure
    provider = CountingProvider(fail)
    with pytest.raises(ImageRequestError) as error:
        generate_image(db, campaign.id, request, identity, provider, storage)
    assert error.value.status_code == status and "private" not in error.value.detail
    row, created = generate_image(db, campaign.id, request, identity, provider, storage)
    assert not created and row.request_state == state
    assert provider.calls == 1 and list(tmp_path.iterdir()) == []


def test_invalid_output_never_becomes_ready_or_creates_a_file(db, tmp_path):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    provider = CountingProvider(lambda *args: ImageOutput(b"fake image", "image/png"))
    with pytest.raises(ImageRequestError) as error:
        generate_image(db, campaign.id, request, identity, provider, storage)
    assert error.value.status_code == 502
    row, _ = generate_image(db, campaign.id, request, identity, provider, storage)
    assert row.request_state == "failed" and row.failure_code == "invalid_image"
    assert row.storage_key is None and list(tmp_path.iterdir()) == []


def test_source_edit_during_provider_rejects_result_and_preserves_original_snapshot(db, tmp_path):
    campaign, source, _, request, identity, storage = arguments(db, tmp_path)
    def change(*args):
        contents.update_content(db, source, ContentUpdate(content={"headline": "Changed while waiting"}))
        return ImageOutput(encoded(), "image/png")
    provider = CountingProvider(change)
    with pytest.raises(ImageRequestError) as error:
        generate_image(db, campaign.id, request, identity, provider, storage)
    assert error.value.status_code == 409
    row, _ = generate_image(db, campaign.id, request, identity, provider, storage)
    assert row.request_state == "failed" and row.source_snapshot["content"]["headline"] == "Test message"
    assert list(tmp_path.iterdir()) == [] and provider.calls == 1


def test_storage_failure_never_claims_success(db, tmp_path, monkeypatch):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    def fail(*args):
        raise ImageStorageError("private path")
    monkeypatch.setattr(storage, "put", fail)
    with pytest.raises(ImageRequestError) as error:
        generate_image(db, campaign.id, request, identity, CountingProvider(), storage)
    assert error.value.status_code == 503 and "private" not in error.value.detail
    row = db.query(ImageGeneration).one()
    assert row.request_state == "failed" and row.storage_key is None


def test_ready_commit_failure_cleans_proven_orphan_and_blocks_provider_replay(db, tmp_path, monkeypatch):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    def fail(*args, **kwargs):
        raise OperationalError("hidden", {}, Exception("private database detail"))
    monkeypatch.setattr(repository, "finish_ready", fail)
    provider = CountingProvider()
    with pytest.raises(ImageRequestError) as error:
        generate_image(db, campaign.id, request, identity, provider, storage)
    assert error.value.status_code == 503
    row, _ = generate_image(db, campaign.id, request, identity, provider, storage)
    assert row.request_state == "outcome_unknown" and provider.calls == 1
    assert list(tmp_path.iterdir()) == []


def test_lost_commit_acknowledgement_retains_referenced_file_and_returns_saved_result(db, tmp_path, monkeypatch):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    finish = repository.finish_ready
    def committed_then_failed(*args, **kwargs):
        finish(*args, **kwargs)
        raise OperationalError("hidden", {}, Exception("private detail"))
    monkeypatch.setattr(repository, "finish_ready", committed_then_failed)
    row, created = generate_image(db, campaign.id, request, identity, CountingProvider(), storage)
    assert created and row.request_state == "ready"
    assert storage.read(row.storage_key) and len(list(tmp_path.iterdir())) == 1


def test_real_provider_is_rejected_before_any_reservation_or_call(db, tmp_path):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    provider = CountingProvider()
    provider.provider_name = "gemini"
    with pytest.raises(ImageRequestError, match="not enabled"):
        generate_image(db, campaign.id, request, identity, provider, storage)
    assert provider.calls == 0 and db.query(ImageGeneration).count() == 0


def test_failed_reload_after_ready_commit_retains_file_and_replay_recovers(db, tmp_path, monkeypatch):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    refresh = db.refresh
    def unavailable(instance, *args, **kwargs):
        if isinstance(instance, ImageGeneration) and list(tmp_path.iterdir()):
            raise OperationalError("hidden", {}, Exception("private detail"))
        return refresh(instance, *args, **kwargs)
    monkeypatch.setattr(db, "refresh", unavailable)
    provider = CountingProvider()
    with pytest.raises(ImageRequestError, match="was saved"):
        generate_image(db, campaign.id, request, identity, provider, storage)
    row, created = generate_image(db, campaign.id, request, identity, provider, storage)
    assert not created and row.request_state == "ready" and provider.calls == 1
    assert storage.read(row.storage_key)


def test_uncertain_database_state_retains_bytes_for_reconciliation(db, tmp_path, monkeypatch):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    get = db.get
    def unavailable(entity, *args, **kwargs):
        if entity is ImageGeneration and list(tmp_path.iterdir()):
            raise OperationalError("hidden", {}, Exception("private detail"))
        return get(entity, *args, **kwargs)
    def failed_commit(*args, **kwargs):
        raise OperationalError("hidden", {}, Exception("private detail"))
    monkeypatch.setattr(db, "get", unavailable)
    monkeypatch.setattr(repository, "finish_ready", failed_commit)
    with pytest.raises(ImageRequestError, match="uncertain"):
        generate_image(db, campaign.id, request, identity, CountingProvider(), storage)
    assert len(list(tmp_path.iterdir())) == 1  # Never remove a potentially referenced file.
    assert db.query(ImageGeneration).one().request_state == "outcome_unknown"
