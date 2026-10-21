"""Saved image reads, verified file access and independent human review."""

from datetime import datetime, timezone
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.campaign import Campaign
from app.models.generated_content import GeneratedContent
from app.models.image_generation import ImageGeneration
from app.providers.image import ImageOutput
from app.schemas.image_generation import StoredImageResponse
from app.services.image_generation import ImageRequestError, source_is_current
from app.services.image_validation import InvalidImageError, validate_image
from app.storage.images import ImageStorage, ImageStorageError, LocalImageStorage


def get_image_storage():
    return LocalImageStorage(settings.media_root, settings.media_max_bytes)


def get_image(db: Session, image_id: int) -> ImageGeneration:
    row = db.get(ImageGeneration, image_id, populate_existing=True)
    if row is None:
        raise ImageRequestError(404, "Image request not found")
    return row


def describe(db: Session, row: ImageGeneration) -> StoredImageResponse:
    values = {name: getattr(row, name) for name in StoredImageResponse.model_fields if name != "source_is_current"}
    return StoredImageResponse(**values, source_is_current=source_is_current(db, row))


def list_images(db: Session, campaign_id: int, skip: int, limit: int):
    if db.get(Campaign, campaign_id) is None:
        raise ImageRequestError(404, "Campaign not found")
    rows = db.scalars(select(ImageGeneration).where(ImageGeneration.campaign_id == campaign_id)
                      .order_by(ImageGeneration.created_at.desc(), ImageGeneration.id.desc()).offset(skip).limit(limit)).all()
    return [describe(db, row) for row in rows]


def read_verified(row: ImageGeneration, storage: ImageStorage) -> bytes:
    if row.request_state != "ready":
        raise ImageRequestError(409, "Image is not ready")
    try:
        data = storage.read(row.storage_key)
        if len(data) != row.byte_count or hashlib.sha256(data).hexdigest() != row.checksum:
            raise ImageStorageError("Stored image integrity mismatch")
        verified = validate_image(ImageOutput(data, row.mime_type), max_bytes=settings.media_max_bytes)
        if (verified.width, verified.height) != (row.width, row.height):
            raise ImageStorageError("Stored image dimensions mismatch")
        return data
    except (ImageStorageError, InvalidImageError):
        raise ImageRequestError(503, "Stored image is unavailable or failed verification") from None


def review_image(db: Session, image_id: int, review_status: str, storage: ImageStorage):
    row = get_image(db, image_id)
    # Match the generation lock order, then refresh under the image lock.
    db.scalar(select(Campaign).where(Campaign.id == row.campaign_id).with_for_update())
    db.scalar(select(GeneratedContent).where(GeneratedContent.id == row.source_content_id).with_for_update())
    row = db.scalar(select(ImageGeneration).where(ImageGeneration.id == image_id)
                    .with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise ImageRequestError(404, "Image request not found")
    if row.request_state != "ready":
        raise ImageRequestError(409, "Only ready images can be reviewed")
    if review_status == "approved":
        if not source_is_current(db, row):
            raise ImageRequestError(409, "Source text changed or is no longer approved")
        read_verified(row, storage)
    row.review_status = review_status
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return describe(db, row)
