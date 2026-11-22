
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.dependencies.auth import DatabaseSession
from app.api.dependencies.tenant import (
    TENANT_ERRORS, DeletableCampaign, EditableCampaign, EditorTenant, PrivateRoute, ReadableCampaign, ReadTenant,
    WriteTenant,
)
from app.repositories import campaign as campaigns
from app.repositories import generated_content as contents
from app.schemas.campaign import CampaignCreateRequest, CampaignReadResponse, CampaignUpdateRequest
from app.services import campaign as campaign_service
from app.services.auth import recheck_locked_session
from app.services.tenant import BusinessNotFound


router = APIRouter(prefix="/campaigns", tags=["Campaigns"], route_class=PrivateRoute, responses=TENANT_ERRORS)


@router.post(
    "",
    response_model=CampaignReadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(data: CampaignCreateRequest, tenant: EditorTenant, db: DatabaseSession):
    if not campaigns.lock_business_reference(db, tenant.business_id):
        raise BusinessNotFound
    recheck_locked_session(db, tenant.user_id, tenant.session_id)
    return campaigns.create_campaign(db, tenant.business_id, data)


@router.get("", response_model=list[CampaignReadResponse])
def list_campaigns(
    tenant: ReadTenant,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return campaigns.list_campaigns(db, tenant.business_id, skip, limit)


@router.get("/{campaign_id}", response_model=CampaignReadResponse)
def get_campaign(campaign: ReadableCampaign):
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignReadResponse)
def update_campaign(
    campaign: EditableCampaign,
    data: CampaignUpdateRequest,
    tenant: WriteTenant,
    db: DatabaseSession,
):
    try:
        recheck_locked_session(db, tenant.user_id, tenant.session_id)
        return campaign_service.update_campaign(db, campaign, data)
    except campaign_service.CampaignUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ValidationError as exc:
        errors = [
            dict(error, loc=("body", *error["loc"]))
            for error in exc.errors(include_context=False)
        ]
        raise RequestValidationError(errors) from exc


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign: DeletableCampaign, tenant: WriteTenant, db: DatabaseSession):
    contents.lock_campaign_contents(db, tenant.business_id, campaign.id)
    recheck_locked_session(db, tenant.user_id, tenant.session_id)
    campaigns.delete_campaign(db, campaign)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
