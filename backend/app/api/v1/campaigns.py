
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from app.services import campaign as campaign_service


router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(data: CampaignCreate, db: DatabaseSession):
    return campaign_service.create_campaign(db, data)


@router.get("", response_model=list[CampaignResponse])
def list_campaigns(
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return campaign_service.list_campaigns(db, skip, limit)


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: DatabaseSession):
    campaign = campaign_service.get_campaign(db, campaign_id)

    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    db: DatabaseSession,
):
    campaign = campaign_service.update_campaign(db, campaign_id, data)

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
