"""Request, provider-output, and persisted text-generation data contracts."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


GenerationTone = Literal["informative", "encouraging", "formal"]
OutputLanguage = Literal["arabic", "english"]


class TextGenerationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    audience: str = Field(min_length=1, max_length=300)
    tone: GenerationTone = "informative"


class TextPackage(BaseModel):
    # Dialect and factual quality require prompt rules and human evaluation;
    # field validation only checks the structure and character limits.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    headline: str = Field(min_length=1, max_length=120)
    slogan: str = Field(min_length=1, max_length=100)
    awareness_message: str = Field(min_length=1, max_length=1200)
    social_caption: str = Field(min_length=1, max_length=600)
    call_to_action: str = Field(min_length=1, max_length=200)


class GeneratedTextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    language: OutputLanguage
    content_type: Literal["text_package"] = "text_package"
    review_status: Literal["draft"] = "draft"
    content: TextPackage


class TextGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: int = Field(gt=0)
    contents: list[GeneratedTextResponse] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def unique_languages(self):
        languages = [item.language for item in self.contents]
        if len(languages) != len(set(languages)):
            raise ValueError("Each language must occur only once")
        # The service must also compare languages against the stored campaign.
        return self


class StoredContentResponse(GeneratedTextResponse):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    campaign_id: int
    generation_id: UUID
    review_status: Literal["draft", "approved", "rejected"]
    provider: str
    model: str
    prompt_version: str
    input_snapshot: dict[str, Any]
    source_references: list[dict[str, Any]]
    created_at: datetime


class SavedTextGenerationResponse(TextGenerationResponse):
    contents: list[StoredContentResponse] = Field(min_length=1, max_length=2)


class TextPackageUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    headline: str | None = Field(default=None, min_length=1, max_length=120)
    slogan: str | None = Field(default=None, min_length=1, max_length=100)
    awareness_message: str | None = Field(default=None, min_length=1, max_length=1200)
    social_caption: str | None = Field(default=None, min_length=1, max_length=600)
    call_to_action: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def require_non_null_changes(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one text field to edit")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Text fields cannot be null")
        return self


class ContentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: TextPackageUpdate | None = None
    review_status: Literal["draft", "approved", "rejected"] | None = None

    @model_validator(mode="after")
    def validate_edit_and_review(self):
        if not self.model_fields_set:
            raise ValueError("Provide content or review_status")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Supplied fields cannot be null")
        if self.content is not None and self.review_status not in {None, "draft"}:
            raise ValueError("Edit content first, then approve or reject it in a separate request")
        return self
