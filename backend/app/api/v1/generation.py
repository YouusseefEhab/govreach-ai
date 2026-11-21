from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.providers.gemini import get_text_provider
from app.providers.text import GenerationError, TextProvider
from app.schemas.generation import (
    CampaignAudienceGenerationRequest,
    ContentUpdate,
    SavedTextGenerationResponse,
    StoredContentResponse,
    TextGenerationRequest,
)
from app.services import generation as generation_service


router = APIRouter(tags=["Generated Content"])
DatabaseSession = Annotated[Session, Depends(get_db)]
Provider = Annotated[TextProvider, Depends(get_text_provider)]


@router.post(
    "/campaigns/{campaign_id}/generate-text",
    response_model=SavedTextGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    description=(
        "Generate and save draft Egyptian Arabic/English text. Marketing campaigns use their "
        "stored target audience when audience is omitted. Legacy campaigns require audience. "
        "Human review is required. Each call creates a generation and may consume provider quota or credits."
    ),
    responses={404: {"description": "Campaign not found"}, 502: {"description": "Invalid provider output"},
               503: {"description": "Provider or storage unavailable"}, 504: {"description": "Provider timeout"}},
)
def generate_text(
    campaign_id: int,
    data: TextGenerationRequest | CampaignAudienceGenerationRequest,
    db: DatabaseSession,
    provider: Provider,
):
    try:
        return generation_service.generate_text(db, campaign_id, data, provider)
    except ValidationError as exc:
        errors = [
            dict(error, loc=("body", *error["loc"]))
            for error in exc.errors(include_url=False, include_context=False)
        ]
        raise RequestValidationError(errors) from None
    except GenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None


@router.get("/campaigns/{campaign_id}/contents", response_model=list[StoredContentResponse])
def list_contents(
    campaign_id: int, db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    try:
        return generation_service.list_contents(db, campaign_id, skip, limit)
    except GenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None


@router.get("/contents/{content_id}", response_model=StoredContentResponse)
def get_content(content_id: int, db: DatabaseSession):
    try:
        return generation_service.get_content(db, content_id)
    except GenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None


@router.patch(
    "/contents/{content_id}", response_model=StoredContentResponse,
    description="Edit selected text fields or set draft/approved/rejected. Editing resets the selected package to draft. Approve or reject in a separate request after editing. Approval does not publish the campaign.",
)
def update_content(content_id: int, data: ContentUpdate, db: DatabaseSession):
    try:
        return generation_service.update_content(db, content_id, data)
    except GenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
