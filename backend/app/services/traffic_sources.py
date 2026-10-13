"""Small local source catalogue; no live web retrieval or legal interpretation."""

from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "traffic_safety.json"
NonEmptyText = Annotated[str, Field(min_length=1)]


class TrafficSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: NonEmptyText
    topic: Literal["seat_belts", "speeding", "distracted_driving", "general"]
    title: NonEmptyText
    publisher: NonEmptyText
    url: HttpUrl
    section: NonEmptyText
    checked_on: date
    keywords: list[NonEmptyText]
    facts: list[NonEmptyText] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.url.scheme != "https" or self.url.host not in {"www.who.int", "who.int"}:
            raise ValueError("The initial catalogue accepts official WHO HTTPS sources only")
        if self.topic != "general" and not self.keywords:
            raise ValueError("Topic sources need matching keywords")
        return self


class SourceCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: NonEmptyText
    sources: list[TrafficSource] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_catalogue(self):
        if len({source.id for source in self.sources}) != len(self.sources):
            raise ValueError("Source IDs must be unique")
        if not any(source.topic == "general" for source in self.sources):
            raise ValueError("A general fallback source is required")
        return self


def select_sources(title: str, objective: str) -> list[dict]:
    catalogue = SourceCatalogue.model_validate_json(CATALOGUE_PATH.read_text(encoding="utf-8"))
    text = f"{title} {objective}".casefold()
    selected = [
        source for source in catalogue.sources
        if source.topic != "general" and any(keyword.casefold() in text for keyword in source.keywords)
    ]
    if not selected:
        selected = [source for source in catalogue.sources if source.topic == "general"]
    return [
        {
            **source.model_dump(mode="json", exclude={"keywords"}),
            "catalogue_version": catalogue.version,
            "scope": "general_road_safety_not_egyptian_law",
            "usage": "supplied_to_generation_prompt",
        }
        for source in selected
    ]
