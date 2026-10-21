
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.campaign import Campaign
from app.models.image_generation import ImageGeneration
from app.services.image_library import get_image_storage
from app.storage.images import ImageStorageError

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
    campaign = db.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())

    if campaign is None:
        return False

    keys = list(db.scalars(select(ImageGeneration.storage_key).where(
        ImageGeneration.campaign_id == campaign_id, ImageGeneration.storage_key.is_not(None))))
    campaign_repository.delete_campaign(db, campaign)
    # Delete only after the DB commit succeeds. Failures remain retryable orphans.
    for key in keys:
        try:
            get_image_storage().delete(key)
        except ImageStorageError:
            logging.getLogger(__name__).warning("Image cleanup pending for storage key %s", key)
    return True
