
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CampaignLanguage = Literal["arabic", "english", "both"]


class CampaignCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    domain: str = Field(default="traffic_safety", min_length=1, max_length=100)
    objective: str = Field(min_length=1)
    language: CampaignLanguage = "both"


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=1, max_length=100)
    objective: str | None = Field(default=None, min_length=1)
    language: CampaignLanguage | None = None
    status: Literal["draft"] | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    domain: str
    objective: str
    language: str
    status: str
    created_at: datetime
