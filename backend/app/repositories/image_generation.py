from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.image_generation import ImageGeneration


def find_by_key(db: Session, campaign_id: int, key: str) -> ImageGeneration | None:
    return db.scalar(select(ImageGeneration).where(
        ImageGeneration.campaign_id == campaign_id, ImageGeneration.idempotency_key == key,
    ))


def create_reservation(db: Session, **values) -> ImageGeneration:
    row = ImageGeneration(**values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def claim_reserved(db: Session, image_id: int) -> bool:
    """Only one caller may claim a reserved request; no provider call here."""
    result = db.execute(update(ImageGeneration).where(
        ImageGeneration.id == image_id, ImageGeneration.request_state == "reserved",
    ).values(request_state="generating", updated_at=datetime.now(timezone.utc)))
    db.commit()
    return result.rowcount == 1


def mark_outcome_unknown(db: Session, image_id: int, code: str = "interrupted_request") -> bool:
    result = db.execute(update(ImageGeneration).where(
        ImageGeneration.id == image_id, ImageGeneration.request_state == "generating",
    ).values(request_state="outcome_unknown", failure_code=code, updated_at=datetime.now(timezone.utc)))
    db.commit()
    return result.rowcount == 1


def finish_failed(db: Session, image_id: int, code: str) -> bool:
    result = db.execute(update(ImageGeneration).where(
        ImageGeneration.id == image_id, ImageGeneration.request_state == "generating",
    ).values(request_state="failed", failure_code=code, updated_at=datetime.now(timezone.utc)))
    db.commit()
    return result.rowcount == 1


def finish_ready(db: Session, image_id: int, *, key: str, mime_type: str,
                 width: int, height: int, byte_count: int, checksum: str) -> bool:
    result = db.execute(update(ImageGeneration).where(
        ImageGeneration.id == image_id, ImageGeneration.request_state == "generating",
    ).values(request_state="ready", review_status="draft", failure_code=None,
             storage_key=key, mime_type=mime_type, width=width, height=height,
             byte_count=byte_count, checksum=checksum, updated_at=datetime.now(timezone.utc)))
    db.commit()
    return result.rowcount == 1
