
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.repositories import campaign as campaign_repository
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    MarketingCampaignCreate,
    MarketingCampaignUpdate,
)


class CampaignUpdateError(ValueError):
    pass


def create_campaign(db: Session, data: CampaignCreate | MarketingCampaignCreate):
    return campaign_repository.create_campaign(db, data)


def get_campaign(db: Session, campaign_id: int):
    return campaign_repository.get_campaign(db, campaign_id)


def list_campaigns(db: Session, skip: int = 0, limit: int = 20):
    return campaign_repository.list_campaigns(db, skip, limit)


def update_campaign(db: Session, campaign_id: int, data: CampaignUpdate):
    # Lock the row through validation and write so concurrent PATCHes cannot mix budget fields.
    campaign = campaign_repository.get_campaign_for_update(db, campaign_id)

    if campaign is None:
        return None

    if "campaign_type" in data.model_fields_set and data.campaign_type != campaign.campaign_type:
        raise CampaignUpdateError("Campaign type cannot be changed")
    if campaign.campaign_type == "marketing":
        data = _validate_marketing_update(campaign, data)
    return campaign_repository.update_campaign(db, campaign, data)


def _validate_marketing_update(
    campaign: Campaign, data: CampaignUpdate
) -> MarketingCampaignUpdate:
    patch = data.model_dump(exclude_unset=True)
    if campaign.domain != "marketing" or patch.get("domain", campaign.domain) != campaign.domain:
        raise CampaignUpdateError("Marketing campaign domain cannot be changed")
    if "status" in patch and patch["status"] is None:
        raise CampaignUpdateError("Marketing campaign status must be draft")

    update = MarketingCampaignUpdate.model_validate(patch)
    merged = {
        field: getattr(campaign, field)
        for field in MarketingCampaignCreate.model_fields
        if field != "budget"
    }
    if campaign.budget_amount is not None or campaign.budget_currency is not None:
        merged["budget"] = {
            "amount": str(campaign.budget_amount) if campaign.budget_amount is not None else None,
            "currency": campaign.budget_currency,
        }
    merged.update(update.model_dump(exclude_unset=True))
    MarketingCampaignCreate.model_validate(merged)
    return update


def delete_campaign(db: Session, campaign_id: int) -> bool:
    campaign = campaign_repository.get_campaign(db, campaign_id)

    if campaign is None:
        return False

    campaign_repository.delete_campaign(db, campaign)
    return True
