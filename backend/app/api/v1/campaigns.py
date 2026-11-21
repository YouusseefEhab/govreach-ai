
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.campaign import (
    CampaignCreate,
    CampaignReadResponse,
    CampaignUpdate,
    MarketingCampaignCreate,
    MarketingCampaignUpdate,
)
from app.services import campaign as campaign_service


router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=CampaignReadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(data: CampaignCreate | MarketingCampaignCreate, db: DatabaseSession):
    return campaign_service.create_campaign(db, data)


@router.get("", response_model=list[CampaignReadResponse])
def list_campaigns(
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return campaign_service.list_campaigns(db, skip, limit)


@router.get("/{campaign_id}", response_model=CampaignReadResponse)
def get_campaign(campaign_id: int, db: DatabaseSession):
    campaign = campaign_service.get_campaign(db, campaign_id)

    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return campaign


@router.patch("/{campaign_id}", response_model=CampaignReadResponse)
def update_campaign(
    campaign_id: int,
    data: MarketingCampaignUpdate | CampaignUpdate,
    db: DatabaseSession,
):
    try:
        campaign = campaign_service.update_campaign(db, campaign_id, data)
    except campaign_service.CampaignUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ValidationError as exc:
        errors = [
            dict(error, loc=("body", *error["loc"]))
            for error in exc.errors(include_context=False)
        ]
        raise RequestValidationError(errors) from exc

    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: int, db: DatabaseSession):
    deleted = campaign_service.delete_campaign(db, campaign_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
