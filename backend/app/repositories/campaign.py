
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignUpdate, MarketingCampaignCreate


def _campaign_columns(values: dict) -> dict:
    if "budget" in values:
        budget = values.pop("budget")
        values["budget_amount"] = Decimal(budget["amount"]) if budget is not None else None
        values["budget_currency"] = budget["currency"] if budget is not None else None
    return values


def create_campaign(db: Session, data: CampaignCreate | MarketingCampaignCreate) -> Campaign:
    campaign = Campaign(**_campaign_columns(data.model_dump()))
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def get_campaign(db: Session, campaign_id: int) -> Campaign | None:
    return db.get(Campaign, campaign_id)


def get_campaign_for_update(db: Session, campaign_id: int) -> Campaign | None:
    statement = (
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return db.scalar(statement)


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
    if campaign.campaign_type == "marketing":
        values = data.model_dump(exclude_unset=True, exclude={"campaign_type", "domain"})
    else:
        values = data.model_dump(
            include={"title", "domain", "objective", "language", "status"},
            exclude_unset=True,
            exclude_none=True,
        )
    for field, value in _campaign_columns(values).items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(db: Session, campaign: Campaign) -> None:
    db.delete(campaign)
    db.commit()
