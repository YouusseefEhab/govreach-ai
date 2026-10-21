"""Image generation, metadata and independent review contracts."""

from datetime import datetime
from typing import Any
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ImageGenerationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    source_content_id: int = Field(gt=0)
    visual_brief: str = Field(min_length=1, max_length=2000)
    style: Literal["illustration", "photorealistic"] = "illustration"


class ImageRequestIdentity(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class ImageReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_status: Literal["draft", "approved", "rejected"]


class StoredImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    campaign_id: int
    source_content_id: int
    idempotency_key: str
    request_state: Literal["reserved", "generating", "ready", "failed", "outcome_unknown"]
    review_status: Literal["draft", "approved", "rejected"]
    source_is_current: bool
    source_snapshot: dict[str, Any]
    source_references: list[dict[str, Any]]
    visual_brief: str
    style: str
    provider: str
    model: str
    prompt_version: str
    mime_type: str | None
    width: int | None
    height: int | None
    byte_count: int | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
