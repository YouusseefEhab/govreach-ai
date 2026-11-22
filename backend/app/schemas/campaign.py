
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    computed_field,
    model_validator,
)


CampaignLanguage = Literal["arabic", "english", "both"]
MarketingChannel = Literal["social", "email", "search", "website", "print"]
BudgetCurrency = Literal["EGP", "USD"]
BusinessName = Annotated[str, Field(min_length=1, max_length=120)]
OfferSummary = Annotated[str, Field(min_length=1, max_length=1000)]
TargetAudience = Annotated[str, Field(min_length=1, max_length=300)]
CampaignBrief = Annotated[str, Field(max_length=3000)]

_OWNERSHIP_FIELDS = {
    "business", "businessid", "tenant", "tenantid", "role", "membership", "membershiprole",
    "owner", "ownerid", "owneruserid", "ownership", "userid", "createdby", "createdbyuserid",
}


def _reject_ownership(data):
    if isinstance(data, dict) and any(
        key.replace("_", "").replace("-", "").casefold() in _OWNERSHIP_FIELDS for key in data
    ):
        raise ValueError("Campaign business, ownership, and membership role are assigned by the server")
    return data


def _distinct_channels(channels: list[MarketingChannel]) -> list[MarketingChannel]:
    if len(channels) != len(set(channels)):
        raise ValueError("Marketing channels must be distinct")
    return channels


MarketingChannels = Annotated[
    list[MarketingChannel], Field(max_length=5), AfterValidator(_distinct_channels)
]


class CampaignBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: str = Field(strict=True, pattern=r"^[0-9]{1,12}(\.[0-9]{1,2})?$")
    currency: BudgetCurrency


class _CampaignCreateFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    objective: str = Field(min_length=1)
    language: CampaignLanguage = "both"


class CampaignCreate(_CampaignCreateFields):
    campaign_type: None = None
    domain: str = Field(default="traffic_safety", min_length=1, max_length=100)


class MarketingCampaignCreate(_CampaignCreateFields):
    campaign_type: Literal["marketing"]
    domain: str = Field(default="marketing", min_length=1, max_length=100)
    objective: str = Field(min_length=1, max_length=2000)
    business_name: BusinessName
    offer_summary: OfferSummary
    target_audience: TargetAudience
    budget: CampaignBudget | None = None
    channels: MarketingChannels | None = Field(default_factory=list)
    brief: CampaignBrief | None = None

    @model_validator(mode="after")
    def set_marketing_domain(self):
        self.domain = "marketing"
        return self


class CampaignUpdate(BaseModel):
    # Keep extra input until the service knows which workflow the stored row uses.
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=1, max_length=100)
    objective: str | None = Field(default=None, min_length=1)
    language: CampaignLanguage | None = None
    status: Literal["draft"] | None = None
    campaign_type: Literal["marketing"] | None = None


class MarketingCampaignUpdate(CampaignUpdate):
    model_config = ConfigDict(extra="ignore")

    business_name: BusinessName | None = None
    offer_summary: OfferSummary | None = None
    target_audience: TargetAudience | None = None
    budget: CampaignBudget | None = None
    channels: MarketingChannels | None = None
    brief: CampaignBrief | None = None


CampaignCreateRequest = Annotated[CampaignCreate | MarketingCampaignCreate, BeforeValidator(_reject_ownership)]
CampaignUpdateRequest = Annotated[MarketingCampaignUpdate | CampaignUpdate, BeforeValidator(_reject_ownership)]


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    title: str
    domain: str
    objective: str
    language: str
    status: str
    created_at: datetime


class MarketingCampaignResponse(CampaignResponse):
    campaign_type: Literal["marketing"]
    business_name: str | None
    offer_summary: str | None
    target_audience: str | None
    channels: list[MarketingChannel] | None
    brief: str | None
    budget_amount: Decimal | None = Field(exclude=True)
    budget_currency: BudgetCurrency | None = Field(exclude=True)

    @computed_field
    @property
    def budget(self) -> CampaignBudget | None:
        if self.budget_amount is None or self.budget_currency is None:
            return None
        return CampaignBudget(amount=format(self.budget_amount, ".2f"), currency=self.budget_currency)


def _response_type(campaign):
    campaign_type = (
        campaign.get("campaign_type")
        if isinstance(campaign, dict)
        else getattr(campaign, "campaign_type", None)
    )
    return "marketing" if campaign_type == "marketing" else "legacy"


CampaignReadResponse = Annotated[
    Annotated[MarketingCampaignResponse, Tag("marketing")]
    | Annotated[CampaignResponse, Tag("legacy")],
    Discriminator(_response_type),
]
