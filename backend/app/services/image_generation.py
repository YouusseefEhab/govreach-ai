"""Image reservations and a fake-only, verified-image generation pipeline."""

from copy import deepcopy
import hashlib
import json
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.generated_content import GeneratedContent
from app.models.image_generation import ImageGeneration
from app.repositories import image_generation as repository
from app.schemas.image_generation import ImageGenerationRequest, ImageRequestIdentity
from app.providers.image import ImageProvider, ImageProviderError
from app.services.image_validation import InvalidImageError, validate_image
from app.storage.images import ImageStorage, ImageStorageError, StoredImageFile

logger = logging.getLogger(__name__)


class ImageRequestError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def source_is_current(db: Session, image: ImageGeneration) -> bool:
    source = db.get(GeneratedContent, image.source_content_id, populate_existing=True)
    campaign = db.get(Campaign, image.campaign_id, populate_existing=True)
    return bool(campaign and campaign.domain == "traffic_safety" and source and source.campaign_id == image.campaign_id
                and source.review_status == "approved" and digest(source.content) == image.source_hash)


def reserve_image_request(
    db: Session, campaign_id: int, request: ImageGenerationRequest, identity: ImageRequestIdentity,
) -> tuple[ImageGeneration, bool]:
    # Hash caller inputs separately from the source snapshot: replaying a key
    # returns its original snapshot even if the source was subsequently edited.
    request_hash = digest({"campaign_id": campaign_id, **request.model_dump()})
    existing = repository.find_by_key(db, campaign_id, identity.key)
    if existing:
        if existing.request_hash != request_hash:
            raise ImageRequestError(409, "Request key already belongs to different inputs")
        return existing, False
    campaign = db.get(Campaign, campaign_id)
    source = db.get(GeneratedContent, request.source_content_id, populate_existing=True)
    if not campaign or not source or source.campaign_id != campaign_id:
        raise ImageRequestError(404, "Campaign or source content not found")
    if campaign.domain != "traffic_safety":
        raise ImageRequestError(409, "Image generation supports traffic safety only")
    if source.review_status != "approved":
        raise ImageRequestError(409, "Approve the source text before requesting an image")
    snapshot = {
        "id": source.id, "generation_id": str(source.generation_id), "language": source.language,
        "content": deepcopy(source.content), "input_snapshot": deepcopy(source.input_snapshot),
        "review_status": source.review_status,
    }
    try:
        row = repository.create_reservation(
            db, campaign_id=campaign_id, source_content_id=source.id,
            idempotency_key=identity.key, request_hash=request_hash, source_hash=digest(source.content),
            source_snapshot=snapshot, source_references=deepcopy(source.source_references),
            visual_brief=request.visual_brief, style=request.style,
            provider="fake", model="fake-image-v1", prompt_version="traffic-image-v1",
        )
        return row, True
    except IntegrityError:
        db.rollback()
        # Resolve a competing insert by the same request identity. This must
        # never imply a second provider call or repeat a failed/unknown request.
        existing = repository.find_by_key(db, campaign_id, identity.key)
        if existing and existing.request_hash == request_hash:
            return existing, False
        raise ImageRequestError(409, "Image request identity or source changed; inspect saved requests") from None


def _cleanup(storage: ImageStorage, file: StoredImageFile | None):
    if file is not None:
        try:
            storage.delete(file.key)
        except ImageStorageError:
            logger.warning("Image cleanup pending for storage key %s", file.key)


def _record_failure(db: Session, image_id: int, code: str, *, ambiguous: bool = False):
    try:
        db.rollback()
        if ambiguous:
            repository.mark_outcome_unknown(db, image_id, code)
        else:
            repository.finish_failed(db, image_id, code)
    except SQLAlchemyError:
        db.rollback()
        logger.warning("Image request %s needs state reconciliation", image_id)


def generate_image(
    db: Session, campaign_id: int, request: ImageGenerationRequest, identity: ImageRequestIdentity,
    provider: ImageProvider, storage: ImageStorage, *, max_bytes: int = 10 * 1024 * 1024,
) -> tuple[ImageGeneration, bool]:
    # Explicit budget boundary: no real image provider is enabled in this increment.
    if provider.provider_name != "fake" or provider.model != "fake-image-v1":
        raise ImageRequestError(503, "Live image generation is not enabled")
    row, created = reserve_image_request(db, campaign_id, request, identity)
    if not created:
        return row, False
    image_id = row.id
    if not repository.claim_reserved(db, image_id):
        db.refresh(row)
        return row, False
    # Capture inputs before releasing the read transaction. No database locks or
    # transaction remain open while waiting on a provider.
    brief, snapshot, style = row.visual_brief, deepcopy(row.source_snapshot), row.style
    if not source_is_current(db, row):
        _record_failure(db, image_id, "source_changed")
        raise ImageRequestError(409, "Source text changed before generation")
    db.commit()
    try:
        output = provider.generate(brief, snapshot, style)
    except ImageProviderError as exc:
        _record_failure(db, image_id, exc.code, ambiguous=exc.ambiguous)
        raise ImageRequestError(exc.status_code, exc.detail) from None
    except TimeoutError:
        _record_failure(db, image_id, "provider_timeout", ambiguous=True)
        raise ImageRequestError(504, "Image request timed out; inspect the saved request before retrying") from None
    except Exception as exc:
        logger.warning("Image provider failed with %s", type(exc).__name__)
        _record_failure(db, image_id, "provider_error", ambiguous=True)
        raise ImageRequestError(503, "Image provider outcome is unknown; inspect the saved request") from None
    file = None
    try:
        validated = validate_image(output, max_bytes=max_bytes)
        # Keep source edits/deletion from racing final metadata persistence.
        db.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())
        db.scalar(select(GeneratedContent).where(GeneratedContent.id == request.source_content_id).with_for_update())
        current = db.get(ImageGeneration, image_id, populate_existing=True)
        if current is None or not source_is_current(db, current):
            raise ImageRequestError(409, "Source text changed during generation; image was not saved")
        file = storage.put(validated.data, validated.mime_type)
        if not repository.finish_ready(db, image_id, key=file.key, mime_type=validated.mime_type,
                                       width=validated.width, height=validated.height,
                                       byte_count=file.byte_count, checksum=file.checksum):
            raise ImageRequestError(409, "Image request is no longer generating")
    except InvalidImageError:
        _record_failure(db, image_id, "invalid_image")
        raise ImageRequestError(502, "Provider image failed validation") from None
    except ImageStorageError:
        _cleanup(storage, file)
        _record_failure(db, image_id, "storage_failed")
        raise ImageRequestError(503, "Image storage is unavailable") from None
    except ImageRequestError:
        _cleanup(storage, file)
        _record_failure(db, image_id, "source_or_request_changed")
        raise
    except SQLAlchemyError:
        db.rollback()
        # A commit may have succeeded even if its acknowledgement was lost.
        # Never delete bytes until a successful DB read proves they are unreferenced.
        try:
            current = db.get(ImageGeneration, image_id, populate_existing=True)
            if current is not None and current.request_state == "ready" and file and current.storage_key == file.key:
                return current, True
            _cleanup(storage, file)
        except SQLAlchemyError:
            logger.warning("Image request %s needs database/file reconciliation", image_id)
        _record_failure(db, image_id, "persistence_failed", ambiguous=True)
        raise ImageRequestError(503, "Image persistence is uncertain; inspect the saved request") from None
    # A ready commit is already durable. Do not turn a read failure into deletion.
    try:
        db.refresh(row)
    except SQLAlchemyError:
        db.rollback()
        raise ImageRequestError(503, "Image was saved but could not be reloaded; inspect saved requests") from None
    return row, True
