from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.generated_content import GeneratedContent
from app.schemas.generation import ContentUpdate, OutputLanguage, TextGenerationRequest, TextPackage


def save_text_generation(
    db: Session,
    campaign: Campaign,
    request: TextGenerationRequest,
    packages: dict[OutputLanguage, TextPackage],
    *,
    provider: str,
    model: str,
    prompt_version: str,
    source_references: list[dict] | None = None,
    input_snapshot: dict[str, Any] | None = None,
) -> list[GeneratedContent]:
    """Save one complete generation atomically, preserving earlier generations."""
    expected = {
        "arabic": {"arabic"},
        "english": {"english"},
        "both": {"arabic", "english"},
    }.get(campaign.language)
    if expected is None or set(packages) != expected:
        raise ValueError("Generated languages must exactly match the campaign language")

    # Validate every variant before adding any rows to the session.
    validated = {language: TextPackage.model_validate(package).model_dump() for language, package in packages.items()}
    generation_id = uuid4()
    created_at = datetime.now(timezone.utc)
    if input_snapshot is None:
        input_snapshot = {
            "title": campaign.title,
            "objective": campaign.objective,
            "domain": campaign.domain,
            "language": campaign.language,
            "audience": request.audience,
            "tone": request.tone,
            "arabic_dialect": "egyptian",
        }
    rows = [
        GeneratedContent(
            campaign_id=campaign.id,
            generation_id=generation_id,
            language=language,
            content_type="text_package",
            content=content,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            input_snapshot=deepcopy(input_snapshot),
            source_references=deepcopy(source_references or []),
            review_status="draft",
            created_at=created_at,
        )
        for language, content in sorted(validated.items())
    ]
    try:
        db.add_all(rows)
        db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise
    for row in rows:
        db.refresh(row)
    return rows


def _business_contents(business_id: UUID):
    return select(GeneratedContent).join(Campaign, GeneratedContent.campaign_id == Campaign.id).where(
        Campaign.business_id == business_id
    )


def lock_campaign_contents(db: Session, business_id: UUID, campaign_id: int) -> None:
    # Deletion already holds the campaign lock. Acquire child locks before its expiry check and cascade.
    statement = (
        select(GeneratedContent.id).join(Campaign, GeneratedContent.campaign_id == Campaign.id)
        .where(Campaign.business_id == business_id, GeneratedContent.campaign_id == campaign_id)
        .order_by(GeneratedContent.id).with_for_update(of=GeneratedContent)
    )
    db.execute(statement).close()


def get_content(db: Session, business_id: UUID, content_id: int, *, for_update=False) -> GeneratedContent | None:
    statement = _business_contents(business_id).where(GeneratedContent.id == content_id)
    if for_update:
        # Lock the parent first, matching campaign deletion's lock order.
        parent = (
            select(Campaign.id).join(GeneratedContent, GeneratedContent.campaign_id == Campaign.id)
            .where(Campaign.business_id == business_id, GeneratedContent.id == content_id)
            .with_for_update(read=True, of=Campaign)
        )
        if db.scalar(parent) is None:
            return None
        statement = statement.with_for_update(of=GeneratedContent).execution_options(populate_existing=True)
    return db.scalar(statement)


def update_content(db: Session, content: GeneratedContent, data: ContentUpdate) -> GeneratedContent:
    try:
        if data.content is not None:
            merged = {**content.content, **data.content.model_dump(exclude_unset=True)}
            # Reassign JSON instead of mutating it in place so SQLAlchemy persists it.
            content.content = TextPackage.model_validate(merged).model_dump()
            content.review_status = "draft"
        elif data.review_status is not None:
            content.review_status = data.review_status
        db.commit()
        db.refresh(content)
    except Exception:
        db.rollback()
        raise
    return content


def list_campaign_contents(
    db: Session, business_id: UUID, campaign_id: int, skip: int = 0, limit: int = 20,
) -> list[GeneratedContent]:
    statement = (
        _business_contents(business_id)
        .where(GeneratedContent.campaign_id == campaign_id)
        .order_by(GeneratedContent.created_at.desc(), GeneratedContent.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())
