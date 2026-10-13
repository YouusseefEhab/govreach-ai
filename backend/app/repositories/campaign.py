
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignUpdate


def create_campaign(db: Session, data: CampaignCreate) -> Campaign:
    campaign = Campaign(**data.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def get_campaign(db: Session, campaign_id: int) -> Campaign | None:
    return db.get(Campaign, campaign_id)


def list_campaigns(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[Campaign]:
    statement = (
        select(Campaign)
        .order_by(Campaign.created_at.desc(), Campaign.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def update_campaign(
    db: Session,
    campaign: Campaign,
    data: CampaignUpdate,
) -> Campaign:
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(db: Session, campaign: Campaign) -> None:
    db.delete(campaign)
    db.commit()
