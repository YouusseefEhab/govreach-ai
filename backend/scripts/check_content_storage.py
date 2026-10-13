"""Verify PostgreSQL storage inside an outer transaction that is rolled back."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models.generated_content import GeneratedContent
from app.repositories import campaign as campaigns
from app.repositories import generated_content as contents
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.schemas.generation import TextGenerationRequest, TextPackage


def check_storage():
    if engine.dialect.name != "postgresql":
        raise ValueError("This diagnostic is intended for PostgreSQL")
    with engine.connect() as connection:
        outer = connection.begin()
        try:
            # Repository commits release savepoints, leaving the outer transaction
            # intact. Its rollback removes all temporary rows created here.
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                campaign = campaigns.create_campaign(db, CampaignCreate(
                    title="GovReach storage diagnostic (rolled back)",
                    objective="Verify content storage", language="both",
                ))
                campaign_id = campaign.id
                request = TextGenerationRequest(audience="Test audience")
                packages = {
                    "arabic": TextPackage(**{
                        field: "اربط الحزام قبل ما تتحرك." for field in TextPackage.model_fields
                    }),
                    "english": TextPackage(**{
                        field: "Buckle up before setting off." for field in TextPackage.model_fields
                    }),
                }
                metadata = {"provider": "fake", "model": "storage-test", "prompt_version": "test-v1"}
                first = contents.save_text_generation(db, campaign, request, packages, **metadata)
                assert len(first) == 2
                assert first[0].generation_id == first[1].generation_id
                assert first[0].content["headline"] == "اربط الحزام قبل ما تتحرك."
                assert first[0].created_at.utcoffset().total_seconds() == 0
                campaigns.update_campaign(db, campaign, CampaignUpdate(title="Updated test title"))
                second = contents.save_text_generation(db, campaign, request, packages, **metadata)
                assert second[0].generation_id != first[0].generation_id
                assert first[0].input_snapshot["title"] != second[0].input_snapshot["title"]
                assert len(contents.list_campaign_contents(db, campaign_id)) == 4
                campaigns.delete_campaign(db, campaign)
                db.expire_all()
                assert db.scalar(select(func.count()).select_from(GeneratedContent).where(
                    GeneratedContent.campaign_id == campaign_id,
                )) == 0
        finally:
            outer.rollback()
    with engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(GeneratedContent).where(
            GeneratedContent.campaign_id == campaign_id,
        )).scalar() == 0
    print("PostgreSQL storage checks passed: bilingual JSON, UTC timestamps, history, and cascade deletion.")
    print("All diagnostic rows were rolled back. No AI API calls were made.")


if __name__ == "__main__":
    try:
        check_storage()
    except Exception:
        print("Storage diagnostic failed. Check PostgreSQL connectivity and run alembic upgrade head.")
        raise SystemExit(1)
    finally:
        engine.dispose()
