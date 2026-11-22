from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies.auth import DatabaseSession
from app.api.dependencies.tenant import TENANT_ERRORS, EditableCampaign, PrivateRoute, ReadableCampaign, ReadTenant, WriteTenant
from app.models import GeneratedContent
from app.providers.gemini import get_text_provider
from app.providers.text import GenerationError, TextProvider
from app.repositories import generated_content as contents
from app.schemas.generation import (
    CampaignAudienceGenerationRequest,
    ContentUpdate,
    SavedTextGenerationResponse,
    StoredContentResponse,
    TextGenerationRequest,
)
from app.services import generation as generation_service
from app.services.auth import recheck_locked_session
from app.services.tenant import require_role


router = APIRouter(tags=["Generated Content"], route_class=PrivateRoute, responses=TENANT_ERRORS)
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
    campaign: EditableCampaign,
    tenant: WriteTenant,
    data: TextGenerationRequest | CampaignAudienceGenerationRequest,
    db: DatabaseSession,
    provider: Provider,
):
    try:
        return generation_service.generate_text(db, tenant, campaign, data, provider)
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
    campaign: ReadableCampaign, tenant: ReadTenant, db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return contents.list_campaign_contents(db, tenant.business_id, campaign.id, skip, limit)


@router.get("/contents/{content_id}", response_model=StoredContentResponse)
def get_content(content_id: int, tenant: ReadTenant, db: DatabaseSession):
    content = contents.get_content(db, tenant.business_id, content_id)
    if content is None:
        raise HTTPException(404, "Generated content not found")
    return content


def editable_content(content_id: int, tenant: WriteTenant, db: DatabaseSession) -> GeneratedContent:
    content = contents.get_content(db, tenant.business_id, content_id, for_update=True)
    if content is None:
        raise HTTPException(404, "Generated content not found")
    require_role(tenant, "editor")
    return content


@router.patch(
    "/contents/{content_id}", response_model=StoredContentResponse,
    description="Edit selected text fields or set draft/approved/rejected. Editing resets the selected package to draft. Approve or reject in a separate request after editing. Approval does not publish the campaign.",
)
def update_content(
    content: Annotated[GeneratedContent, Depends(editable_content)], tenant: WriteTenant,
    data: ContentUpdate, db: DatabaseSession,
):
    if "review_status" in data.model_fields_set:
        require_role(tenant, "owner")
    try:
        recheck_locked_session(db, tenant.user_id, tenant.session_id)
        return contents.update_content(db, content, data)
    except SQLAlchemyError:
        raise HTTPException(503, "Content update could not be saved; check database availability") from None
