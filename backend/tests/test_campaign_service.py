from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import Business, Campaign
from app.repositories import campaign as campaigns
from app.schemas.campaign import CampaignUpdate, MarketingCampaignCreate
from app.services import campaign as campaign_service


@pytest.fixture
def business_id(db):
    business = Business(display_name="Campaign service test shop")
    db.add(business)
    db.commit()
    return business.id


def test_marketing_budget_is_persisted_and_cleared_as_a_pair(db, business_id):
    campaign = campaigns.create_campaign(db, business_id, MarketingCampaignCreate(
        campaign_type="marketing",
        title="Spring offers",
        objective="Increase orders",
        business_name="Cairo Bakery",
        offer_summary="Weekend pastry box",
        target_audience="Local families",
        budget={"amount": "999999999999.99", "currency": "USD"},
    ))
    assert campaign.budget_amount == Decimal("999999999999.99")
    assert campaign.budget_currency == "USD"

    updated = campaign_service.update_campaign(db, campaign, CampaignUpdate(title="Weekend offers"))
    assert updated.budget_amount == Decimal("999999999999.99")
    assert updated.budget_currency == "USD"

    cleared = campaign_service.update_campaign(db, campaign, CampaignUpdate(budget=None))
    assert cleared.budget_amount is None
    assert cleared.budget_currency is None


def test_marketing_patch_validates_the_merged_record(db, business_id):
    campaign = Campaign(
        campaign_type="marketing", domain="marketing", title="Spring offers",
        objective="Increase orders", business_name="Cairo Bakery", offer_summary="Weekend pastry box",
        business_id=business_id,
    )
    db.add(campaign)
    db.commit()

    with pytest.raises(ValidationError, match="target_audience"):
        campaign_service.update_campaign(db, campaign, CampaignUpdate(title="Weekend offers"))
    assert campaign.title == "Spring offers"

    updated = campaign_service.update_campaign(db, campaign, CampaignUpdate(
        title="Weekend offers", target_audience="  Local families  ",
    ))
    assert updated.title == "Weekend offers"
    assert updated.target_audience == "Local families"
