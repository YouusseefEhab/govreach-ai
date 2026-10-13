from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

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
    snapshot = {
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
            input_snapshot=deepcopy(snapshot),
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


def get_content(db: Session, content_id: int) -> GeneratedContent | None:
    return db.get(GeneratedContent, content_id)


def get_content_for_update(db: Session, content_id: int) -> GeneratedContent | None:
    return db.scalar(select(GeneratedContent).where(GeneratedContent.id == content_id).with_for_update())


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
    db: Session, campaign_id: int, skip: int = 0, limit: int = 20,
) -> list[GeneratedContent]:
    statement = (
        select(GeneratedContent)
        .where(GeneratedContent.campaign_id == campaign_id)
        .order_by(GeneratedContent.created_at.desc(), GeneratedContent.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())
