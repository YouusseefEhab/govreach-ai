"""Initial image request contract; not yet exposed as a public API."""

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
