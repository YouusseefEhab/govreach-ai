from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


MembershipRole = Literal["owner", "editor", "viewer"]
DisplayName = Annotated[str, Field(min_length=1, max_length=120)]
Locale = Annotated[str, Field(max_length=35, pattern=r"^[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*$")]


class BusinessUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    display_name: DisplayName | None = None
    description: str | None = Field(default=None, max_length=3000)
    website_url: AnyHttpUrl | None = None
    default_locale: Locale | None = None

    @field_validator("website_url")
    @classmethod
    def validate_website(cls, website: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if website is not None and (website.username is not None or website.password is not None):
            raise ValueError("Website URL cannot contain credentials")
        return website

    @model_validator(mode="after")
    def validate_display_name(self):
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("Business display name cannot be null")
        return self


class BusinessCreate(BusinessUpdate):
    display_name: DisplayName


class BusinessRead(BaseModel):
    id: UUID
    display_name: str
    description: str | None
    website_url: str | None
    default_locale: str | None
    created_at: datetime
    updated_at: datetime
    role: MembershipRole
