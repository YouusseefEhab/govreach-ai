from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.generated_content import GeneratedContent
from app.repositories import campaign as campaigns
from app.repositories import generated_content as contents
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.schemas.generation import TextGenerationRequest, TextPackage


def package(language):
    text = "اربط حزامك قبل ما تتحرك." if language == "arabic" else "Buckle up before setting off."
    return TextPackage(**{field: text for field in TextPackage.model_fields})


def create_campaign(db, language="both"):
    return campaigns.create_campaign(db, CampaignCreate(
        title="Seat belt awareness", objective="Encourage seat belt use", language=language,
    ))


def save(db, campaign, **changes):
    languages = ["arabic", "english"] if campaign.language == "both" else [campaign.language]
    arguments = {
        "request": TextGenerationRequest(audience="Drivers and passengers"),
        "packages": {language: package(language) for language in languages},
        "provider": "fake", "model": "test-model", "prompt_version": "traffic-text-v1",
        **changes,
    }
    return contents.save_text_generation(db, campaign, **arguments)


def count(db):
    return db.scalar(select(func.count()).select_from(GeneratedContent))


@pytest.mark.parametrize("language", ["arabic", "english", "both"])
def test_save_complete_generation(db, language):
    campaign = create_campaign(db, language)
    rows = save(db, campaign)
    expected = {"arabic", "english"} if language == "both" else {language}
    assert {row.language for row in rows} == expected
    assert len({row.generation_id for row in rows}) == 1
    assert len({row.created_at for row in rows}) == 1
    assert campaign.status == "draft"
    for row in rows:
        assert row.review_status == "draft"
        assert row.provider == "fake"
        assert row.content == package(row.language).model_dump()
        assert row.source_references == []
        assert row.input_snapshot["arabic_dialect"] == "egyptian"
        assert contents.get_content(db, row.id).id == row.id


def test_history_and_snapshot_survive_campaign_edits(db):
    campaign = create_campaign(db)
    first = save(db, campaign)
    snapshot = first[0].input_snapshot.copy()
    campaigns.update_campaign(db, campaign, CampaignUpdate(title="Updated title"))
    second = save(db, campaign)
    assert first[0].generation_id != second[0].generation_id
    assert contents.get_content(db, first[0].id).input_snapshot == snapshot
    assert second[0].input_snapshot["title"] == "Updated title"
    assert count(db) == 4
    all_rows = contents.list_campaign_contents(db, campaign.id)
    assert [row.id for row in all_rows[:2]] == [second[1].id, second[0].id]
    assert contents.list_campaign_contents(db, campaign.id, skip=1, limit=1)[0].id == all_rows[1].id


@pytest.mark.parametrize("languages", [[], ["arabic"], ["english"], ["both"], ["arabic", "english", "french"]])
def test_language_mismatch_does_not_write(db, languages):
    campaign = create_campaign(db)
    save(db, campaign)
    with pytest.raises(ValueError, match="exactly match"):
        save(db, campaign, packages={language: package("english") for language in languages})
    assert count(db) == 2


def test_invalid_second_package_does_not_write(db):
    campaign = create_campaign(db)
    with pytest.raises(ValidationError):
        save(db, campaign, packages={"arabic": package("arabic"), "english": {"headline": "Incomplete"}})
    assert count(db) == 0


def test_database_failure_rolls_back_both_variants_and_session_recovers(db):
    campaign = create_campaign(db)
    original = save(db, campaign)
    # A database constraint failure after validation must roll back the whole save.
    with pytest.raises(IntegrityError):
        save(db, campaign, model=None)
    assert count(db) == 2
    assert contents.get_content(db, original[0].id) is not None
    assert len(save(db, campaign)) == 2
    assert count(db) == 4


def test_campaign_delete_cascades_only_its_contents(db):
    first = create_campaign(db)
    second = create_campaign(db)
    save(db, first)
    kept = save(db, second)
    first_id = first.id
    campaigns.delete_campaign(db, first)
    db.expire_all()
    assert contents.list_campaign_contents(db, first_id) == []
    assert {row.id for row in contents.list_campaign_contents(db, second.id)} == {row.id for row in kept}
    assert count(db) == 2


def test_no_cross_campaign_results_or_missing_content(db):
    campaign = create_campaign(db)
    save(db, campaign)
    other = create_campaign(db)
    assert contents.list_campaign_contents(db, other.id) == []
    assert contents.get_content(db, 999999) is None


def test_generation_language_uniqueness_in_database(db):
    campaign = create_campaign(db)
    original = save(db, campaign)[0]
    duplicate = GeneratedContent(
        campaign_id=campaign.id, generation_id=original.generation_id,
        language=original.language, content=original.content, provider="fake",
        model="test-model", prompt_version="v1", input_snapshot={}, source_references=[],
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert count(db) == 2


@pytest.mark.parametrize("changes", [
    {"campaign_id": 999999}, {"language": "both"},
    {"content_type": "image"}, {"review_status": "published"},
])
def test_database_constraints(db, changes):
    campaign = create_campaign(db)
    row = GeneratedContent(**{
        "campaign_id": campaign.id, "generation_id": uuid4(), "language": "arabic",
        "content_type": "text_package", "content": package("arabic").model_dump(),
        "provider": "fake", "model": "test-model", "prompt_version": "v1",
        "input_snapshot": {}, "source_references": [], "review_status": "draft",
        "created_at": datetime.now(timezone.utc), **changes,
    })
    db.add(row)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert count(db) == 0
