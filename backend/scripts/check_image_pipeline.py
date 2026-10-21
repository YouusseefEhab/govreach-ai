"""Rollback-only PostgreSQL image pipeline check; fake provider, no live mode."""

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models import Campaign, GeneratedContent, ImageGeneration
from app.providers.image import FakeImageProvider
from app.repositories import campaign as campaigns
from app.repositories import generated_content as contents
from app.schemas.campaign import CampaignCreate
from app.schemas.generation import ContentUpdate, TextGenerationRequest, TextPackage
from app.schemas.image_generation import ImageGenerationRequest, ImageRequestIdentity
from app.services.image_generation import generate_image, source_is_current
from app.services.image_validation import validate_image
from app.providers.image import ImageOutput
from app.storage.images import LocalImageStorage


def counts(connection):
    return tuple(connection.scalar(select(func.count()).select_from(model))
                 for model in (Campaign, GeneratedContent, ImageGeneration))


def check_pipeline():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("This diagnostic requires PostgreSQL")
    with TemporaryDirectory(prefix="govreach-image-check-") as directory, engine.connect() as connection:
        outer = connection.begin()
        before = counts(connection)
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                campaign = campaigns.create_campaign(db, CampaignCreate(title="Disposable image pipeline check", objective="Seat belt awareness", language="english"))
                source = contents.save_text_generation(
                    db, campaign, TextGenerationRequest(audience="Drivers"),
                    {"english": TextPackage(**{field: "Buckle up before setting off." for field in TextPackage.model_fields})},
                    provider="fake", model="fake-text", prompt_version="diagnostic",
                )[0]
                contents.update_content(db, source, ContentUpdate(review_status="approved"))
                storage = LocalImageStorage(Path(directory))
                provider = FakeImageProvider()
                request = ImageGenerationRequest(source_content_id=source.id, visual_brief="Parked car, seat belts correctly worn, no text")
                identity = ImageRequestIdentity(key="rollback_image_check")
                row, created = generate_image(db, campaign.id, request, identity, provider, storage)
                assert created and row.request_state == "ready" and row.review_status == "draft"
                assert source_is_current(db, row)
                data = storage.read(row.storage_key)
                assert validate_image(ImageOutput(data, row.mime_type)).width == 32
                replay, created = generate_image(db, campaign.id, request, identity, provider, storage)
                assert not created and replay.id == row.id
                contents.update_content(db, source, ContentUpdate(content={"headline": "Edited after image generation"}))
                assert not source_is_current(db, row)
                assert len(list(Path(directory).iterdir())) == 1
                print("Fake pipeline passed: verified PNG, ready draft metadata, file reload, same-key replay, stale-source detection.")
        finally:
            outer.rollback()
            assert counts(connection) == before
            print("All diagnostic rows rolled back; temporary files removed on exit. No Gemini calls.")
    return 0


if __name__ == "__main__":
    try:
        result = check_pipeline()
    except Exception:
        print("Image pipeline diagnostic failed. Check PostgreSQL, dependencies, migrations and storage configuration.")
        result = 1
    finally:
        engine.dispose()
    raise SystemExit(result)
