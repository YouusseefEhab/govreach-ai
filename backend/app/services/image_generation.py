"""Provider-free image reservation and provenance rules."""

from copy import deepcopy
import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.generated_content import GeneratedContent
from app.models.image_generation import ImageGeneration
from app.repositories import image_generation as repository
from app.schemas.image_generation import ImageGenerationRequest, ImageRequestIdentity


class ImageRequestError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def source_is_current(db: Session, image: ImageGeneration) -> bool:
    source = db.get(GeneratedContent, image.source_content_id, populate_existing=True)
    return bool(source and source.campaign_id == image.campaign_id
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
