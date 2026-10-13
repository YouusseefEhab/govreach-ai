
from sqlalchemy.orm import Session

from app.repositories import campaign as campaign_repository
from app.schemas.campaign import CampaignCreate, CampaignUpdate


def create_campaign(db: Session, data: CampaignCreate):
    return campaign_repository.create_campaign(db, data)


def get_campaign(db: Session, campaign_id: int):
    return campaign_repository.get_campaign(db, campaign_id)


def list_campaigns(db: Session, skip: int = 0, limit: int = 20):
    return campaign_repository.list_campaigns(db, skip, limit)


def update_campaign(db: Session, campaign_id: int, data: CampaignUpdate):
    campaign = campaign_repository.get_campaign(db, campaign_id)

    if campaign is None:
        return None

    return campaign_repository.update_campaign(db, campaign, data)


def delete_campaign(db: Session, campaign_id: int) -> bool:
    campaign = campaign_repository.get_campaign(db, campaign_id)

    if campaign is None:
        return False

    campaign_repository.delete_campaign(db, campaign)
    return True
