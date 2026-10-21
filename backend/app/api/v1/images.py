from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.providers.cloudflare import get_image_provider
from app.providers.image import ImageProviderError
from app.schemas.image_generation import ImageGenerationRequest, ImageRequestIdentity, ImageReviewUpdate, StoredImageResponse
from app.services import image_library as library
from app.services.image_generation import ImageRequestError, generate_image
from app.storage.images import ImageStorage, ImageStorageError

router = APIRouter(tags=["Images"])
DatabaseSession = Annotated[Session, Depends(get_db)]
Storage = Annotated[ImageStorage, Depends(library.get_image_storage)]


def image_provider():
    try:
        return get_image_provider()
    except ImageProviderError as exc:
        raise HTTPException(exc.status_code, exc.detail) from None


def execute(operation):
    try:
        return operation()
    except ImageRequestError as exc:
        raise HTTPException(exc.status_code, exc.detail) from None
    except ImageStorageError:
        raise HTTPException(503, "Image storage is unavailable") from None


@router.post("/campaigns/{campaign_id}/generate-image", response_model=StoredImageResponse, status_code=201,
             responses={200: {"model": StoredImageResponse, "description": "Existing request replay; inspect request_state"},
                        409: {"description": "Conflicting key or ineligible source"},
                        502: {"description": "Invalid provider image"},
                        503: {"description": "Provider or storage unavailable"},
                        504: {"description": "Provider timeout; inspect saved request"}},
             description="Explicit generation from approved text. Consumes provider quota. Required Idempotency-Key: reuse with identical inputs to inspect the original request without generating again. New success: 201; every replay, including failed/pending/unknown: 200. Approval is separate and does not publish.")
def create_image(campaign_id: int, data: ImageGenerationRequest, db: DatabaseSession, storage: Storage,
                 response: Response,
                 idempotency_key: Annotated[str, Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")],
                 provider=Depends(image_provider)):
    def operation():
        row, created = generate_image(db, campaign_id, data, ImageRequestIdentity(key=idempotency_key),
                                      provider, storage, max_bytes=settings.media_max_bytes)
        response.status_code = 201 if created else 200
        return library.describe(db, row)
    return execute(operation)


@router.get("/campaigns/{campaign_id}/images", response_model=list[StoredImageResponse])
def list_images(campaign_id: int, db: DatabaseSession, skip: Annotated[int, Query(ge=0)] = 0,
                limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return execute(lambda: library.list_images(db, campaign_id, skip, limit))


@router.get("/images/{image_id}", response_model=StoredImageResponse)
def get_image(image_id: int, db: DatabaseSession):
    return execute(lambda: library.describe(db, library.get_image(db, image_id)))


@router.get("/images/{image_id}/file", response_class=Response,
            responses={200: {"content": {"image/png": {}, "image/jpeg": {}}}},
            description="Verified preview or download, including drafts/stale images. Consult metadata for review and source eligibility; file access is not publication approval.")
def image_file(image_id: int, db: DatabaseSession, storage: Storage, download: bool = False):
    def operation():
        row = library.get_image(db, image_id)
        data = library.read_verified(row, storage)
        extension = "png" if row.mime_type == "image/png" else "jpg"
        disposition = "attachment" if download else "inline"
        return Response(data, media_type=row.mime_type, headers={
            "Content-Disposition": f'{disposition}; filename="govreach-image-{image_id}.{extension}"',
            "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})
    return execute(operation)


@router.patch("/images/{image_id}", response_model=StoredImageResponse,
              description="Independent image review. Approval requires a verified file and unchanged approved source text. No public publishing.")
def review_image(image_id: int, data: ImageReviewUpdate, db: DatabaseSession, storage: Storage):
    return execute(lambda: library.review_image(db, image_id, data.review_status, storage))
