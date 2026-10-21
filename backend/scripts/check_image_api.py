"""Rollback-only PostgreSQL image API check; fake provider, no AI requests."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.images import image_provider
from app.core.database import engine, get_db
from app.main import app
from app.providers.image import FakeImageProvider
from app.repositories import campaign as campaigns
from app.repositories import generated_content as contents
from app.schemas.campaign import CampaignCreate
from app.schemas.generation import ContentUpdate, TextGenerationRequest, TextPackage
from app.services.image_library import get_image_storage
from app.storage.images import LocalImageStorage
from scripts.check_image_pipeline import counts


def check_api():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("PostgreSQL required")
    previous = app.dependency_overrides.copy()
    with TemporaryDirectory(prefix="govreach-image-api-") as directory, engine.connect() as connection:
        outer = connection.begin()
        before = counts(connection)
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                campaign = campaigns.create_campaign(db, CampaignCreate(title="Disposable image API check", objective="Seat belts", language="english"))
                source = contents.save_text_generation(db, campaign, TextGenerationRequest(audience="Drivers"),
                    {"english": TextPackage(**{field: "Buckle up." for field in TextPackage.model_fields})},
                    provider="fake", model="fake", prompt_version="diagnostic")[0]
                contents.update_content(db, source, ContentUpdate(review_status="approved"))
                storage = LocalImageStorage(Path(directory))
                app.dependency_overrides[get_db] = lambda: db
                app.dependency_overrides[image_provider] = FakeImageProvider
                app.dependency_overrides[get_image_storage] = lambda: storage
                with patch("app.services.campaign.get_image_storage", return_value=storage), TestClient(app) as client:
                    url = f"/api/v1/campaigns/{campaign.id}/generate-image"
                    kwargs = {"json": {"source_content_id": source.id, "visual_brief": "Correct seat belts, no text"},
                              "headers": {"Idempotency-Key": "api_diagnostic"}}
                    created = client.post(url, **kwargs)
                    assert created.status_code == 201
                    image_url = f"/api/v1/images/{created.json()['id']}"
                    assert client.post(url, **kwargs).status_code == 200
                    assert client.get(image_url + "/file").status_code == 200
                    assert client.get(image_url + "/file?download=true").headers["content-disposition"].startswith("attachment;")
                    assert client.patch(image_url, json={"review_status": "approved"}).status_code == 200
                    assert client.patch(f"/api/v1/contents/{source.id}", json={"content": {"headline": "Changed"}}).status_code == 200
                    assert not client.get(image_url).json()["source_is_current"]
                    assert client.patch(image_url, json={"review_status": "approved"}).status_code == 409
                    assert client.delete(f"/api/v1/campaigns/{campaign.id}").status_code == 204
                    assert client.get(image_url).status_code == 404
                    assert list(Path(directory).iterdir()) == []
            print("Image API passed: generation, replay, preview/download, review, stale-source gate and cascade/file cleanup.")
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
            outer.rollback()
            assert counts(connection) == before
            print("Diagnostic rows rolled back; temporary files removed. No AI calls.")


if __name__ == "__main__":
    try:
        check_api()
    except Exception:
        print("Image API diagnostic failed; check PostgreSQL, migrations and dependencies.")
        raise SystemExit(1) from None
    finally:
        engine.dispose()
