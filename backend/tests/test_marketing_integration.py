import json
from decimal import Decimal

import pytest
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.generated_content import GeneratedContent
from app.providers.text import GenerationError


CAMPAIGNS = "/api/v1/campaigns"
CONTENTS = "/api/v1/contents"
PACKAGE_FIELDS = {"headline", "slogan", "awareness_message", "social_caption", "call_to_action"}


@pytest.fixture
def test_engine(migration_db, request):
    # The shared HTTP client uses this migrated engine for each request session.
    config, engine = migration_db
    if getattr(request, "param", False):
        command.upgrade(config, "b7f23e8d10a4")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO campaigns (id, title, domain, objective, language, status, created_at) "
                    "VALUES (:id, 'Seat belts', :domain, 'Encourage seat belt use', "
                    "'both', 'draft', '2026-10-13')"
                ),
                [{"id": 1, "domain": "traffic_safety"}, {"id": 2, "domain": "marketing"}],
            )
    command.upgrade(config, "head")
    return engine


@pytest.fixture
def marketing_campaign(client):
    response = client.post(CAMPAIGNS, json={
        "campaign_type": "marketing",
        "title": "Weekend pastry box",
        "objective": "Increase pickup orders",
        "business_name": "Cairo Bakery",
        "offer_summary": "Assorted pastry box for weekend pickup",
        "target_audience": "Local families",
        "language": "both",
        "budget": {"amount": "4321.5", "currency": "EGP"},
        "channels": ["social", "email"],
        "brief": "Mention weekend pickup.",
    })
    assert response.status_code == 201, response.text
    return response.json()


def stored_budget(engine, campaign_id):
    with Session(engine) as session:
        return session.execute(
            select(Campaign.budget_amount, Campaign.budget_currency).where(Campaign.id == campaign_id)
        ).one()


def persisted_contents(engine):
    with Session(engine) as session:
        return {row.id: row for row in session.scalars(select(GeneratedContent))}


def assert_saved_marketing_generation(response, campaign, provider, *, audience, tone):
    assert response.status_code == 201, response.text
    assert response.json()["campaign_id"] == campaign["id"]
    rows = response.json()["contents"]
    assert len(rows) == 2
    assert len({row["generation_id"] for row in rows}) == 1
    assert {row["language"] for row in rows} == {"arabic", "english"}

    instructions, inputs, languages = provider.calls[-1]
    assert languages == {"arabic", "english"}
    assert inputs == {
        **{key: campaign[key] for key in (
            "title", "objective", "domain", "campaign_type", "business_name", "offer_summary",
            "target_audience", "language", "channels", "brief",
        )},
        "audience": audience,
        "tone": tone,
        "languages": ["arabic", "english"],
        "arabic_dialect": "egyptian",
    }
    snapshot = {
        **inputs,
        "prompt_version": "marketing-text-v1",
        "provider": provider.provider_name,
        "model": provider.model,
    }
    for value in campaign["budget"].values():
        assert value not in instructions
        assert value not in json.dumps(snapshot)
    for row in rows:
        assert row["campaign_id"] == campaign["id"]
        assert row["content_type"] == "text_package"
        assert set(row["content"]) == PACKAGE_FIELDS
        assert row["content"] == provider.marketing_copy[row["language"]]
        assert row["review_status"] == "draft"
        assert row["source_references"] == []
        assert row["input_snapshot"] == snapshot
        for field in ("provider", "model", "prompt_version"):
            assert row[field] == snapshot[field]
    return {row["language"]: row for row in rows}


def test_marketing_crud_persists_update_and_budget_clear(client, test_engine, marketing_campaign):
    campaign_id = marketing_campaign["id"]
    url = f"{CAMPAIGNS}/{campaign_id}"
    assert marketing_campaign["domain"] == "marketing"
    assert marketing_campaign["campaign_type"] == "marketing"
    assert marketing_campaign["budget"] == {"amount": "4321.50", "currency": "EGP"}
    assert client.get(url).json() == marketing_campaign
    assert stored_budget(test_engine, campaign_id) == (Decimal("4321.50"), "EGP")

    changes = {
        "objective": "Grow repeat pickup orders",
        "channels": ["email"],
        "budget": {"amount": "1200.04", "currency": "USD"},
    }
    updated = client.patch(url, json=changes)
    assert updated.status_code == 200, updated.text
    assert client.get(url).json() == updated.json() == {**marketing_campaign, **changes}
    assert stored_budget(test_engine, campaign_id) == (Decimal("1200.04"), "USD")

    cleared = client.patch(url, json={"budget": None})
    assert cleared.status_code == 200, cleared.text
    assert client.get(url).json() == cleared.json() == {**updated.json(), "budget": None}
    assert client.get(CAMPAIGNS).json() == [cleared.json()]
    assert stored_budget(test_engine, campaign_id) == (None, None)


def test_marketing_generation_history_edit_and_review_persist(client, test_engine, provider, marketing_campaign):
    campaign_url = f"{CAMPAIGNS}/{marketing_campaign['id']}"
    generation_url = f"{campaign_url}/generate-text"
    history_url = f"{campaign_url}/contents"
    first = assert_saved_marketing_generation(
        client.post(generation_url, json={}), marketing_campaign, provider,
        audience="Local families", tone="informative",
    )
    assert {row["id"]: row for row in client.get(history_url).json()} == {
        row["id"]: row for row in first.values()
    }

    saved_campaign = client.patch(campaign_url, json={"target_audience": "Saturday shoppers"})
    assert saved_campaign.status_code == 200, saved_campaign.text
    second = assert_saved_marketing_generation(
        client.post(generation_url, json={"audience": "  Office workers  ", "tone": "formal"}),
        saved_campaign.json(), provider, audience="Office workers", tone="formal",
    )
    for language in first:
        assert second[language]["generation_id"] != first[language]["generation_id"]
        assert client.get(f"{CONTENTS}/{first[language]['id']}").json() == first[language]

    english_url = f"{CONTENTS}/{second['english']['id']}"
    arabic_url = f"{CONTENTS}/{second['arabic']['id']}"
    edit = {"headline": "Pick up your weekend pastry box"}
    invalid = client.patch(english_url, json={"content": edit, "review_status": "approved"})
    assert invalid.status_code == 422
    assert client.get(english_url).json() == second["english"]

    edited = client.patch(english_url, json={"content": edit})
    assert edited.status_code == 200, edited.text
    assert edited.json() == {
        **second["english"], "content": {**second["english"]["content"], **edit},
    }
    approved = {**edited.json(), "review_status": "approved"}
    rejected = {**second["arabic"], "review_status": "rejected"}
    for url, expected in ((english_url, approved), (arabic_url, rejected), (english_url, approved)):
        review = client.patch(url, json={"review_status": expected["review_status"]})
        assert review.status_code == 200, review.text
        assert review.json() == expected

    latest_edit = {"slogan": "Make the weekend a pastry weekend"}
    redrafted = client.patch(english_url, json={"content": latest_edit})
    assert redrafted.status_code == 200, redrafted.text
    assert redrafted.json() == {
        **approved, "review_status": "draft", "content": {**approved["content"], **latest_edit},
    }
    expected_history = {row["id"]: row for row in [*first.values(), redrafted.json(), rejected]}
    for _ in range(2):
        listing = client.get(history_url)
        assert listing.status_code == 200
        assert {row["id"]: row for row in listing.json()} == expected_history
        assert client.get(english_url).json() == redrafted.json()
        assert client.get(arabic_url).json() == rejected
        assert client.get(campaign_url).json() == saved_campaign.json()

    assert saved_campaign.json()["status"] == "draft"
    assert len(provider.calls) == 2
    stored = persisted_contents(test_engine)
    assert stored.keys() == expected_history.keys()
    for item_id, expected in expected_history.items():
        assert stored[item_id].content == expected["content"]
        assert stored[item_id].input_snapshot == expected["input_snapshot"]
        assert stored[item_id].source_references == []
        assert stored[item_id].review_status == expected["review_status"]


@pytest.mark.parametrize(("failure", "status", "detail"), [
    ("provider-timeout", 504, "Fake provider timed out"),
    ("invalid-variant", 502, "Generated content does not match the campaign requirements"),
    ("unsupported-claim", 502, "Generated draft contains an unsupported monetary amount"),
    ("database-constraint", 503, "Generated content could not be saved"),
])
def test_failed_generation_leaves_no_partial_bilingual_rows(
    client, test_engine, provider, marketing_campaign, failure, status, detail,
):
    campaign_url = f"{CAMPAIGNS}/{marketing_campaign['id']}"
    generation_url = f"{campaign_url}/generate-text"
    history_url = f"{campaign_url}/contents"
    assert client.post(generation_url, json={}).status_code == 201
    history = client.get(history_url).json()
    assert len(history) == 2

    if failure == "provider-timeout":
        provider.error = GenerationError(504, "Fake provider timed out")
    elif failure == "invalid-variant":
        provider.result = {**provider.marketing_copy, "english": {"headline": "Incomplete draft"}}
    elif failure == "unsupported-claim":
        provider.result = {
            **provider.marketing_copy,
            "english": {**provider.marketing_copy["english"], "headline": "Save 75% on your pastry box"},
        }
    else:
        provider.model = None  # Violate the real generated_contents NOT NULL constraint.
    failed = client.post(generation_url, json={})
    assert failed.status_code == status, failed.text
    assert failed.json()["detail"].startswith(detail)
    assert len(provider.calls) == 2
    assert client.get(history_url).json() == history
    assert persisted_contents(test_engine).keys() == {row["id"] for row in history}


@pytest.mark.parametrize("location", ["brief", "audience"])
def test_pasted_credentials_leave_existing_history_intact(
    client, test_engine, provider, marketing_campaign, caplog, location,
):
    campaign_url = f"{CAMPAIGNS}/{marketing_campaign['id']}"
    generation_url = f"{campaign_url}/generate-text"
    history_url = f"{campaign_url}/contents"
    assert client.post(generation_url, json={}).status_code == 201
    history = client.get(history_url).json()
    token = "integration-fake-bearer-0123456789"
    pasted = f"Authorization: Bearer {token}"
    body = {}
    if location == "brief":
        assert client.patch(campaign_url, json={"brief": pasted}).status_code == 200
    else:
        body["audience"] = pasted

    blocked = client.post(generation_url, json=body)
    assert blocked.status_code == 422
    assert blocked.json() == {
        "detail": f"Remove credential-like text from {location} before generating a draft.",
    }
    assert token not in blocked.text
    assert token not in caplog.text
    assert len(provider.calls) == 1
    assert client.get(history_url).json() == history
    stored = persisted_contents(test_engine)
    assert stored.keys() == {row["id"] for row in history}
    assert all(token not in json.dumps(row.input_snapshot) for row in stored.values())


@pytest.mark.parametrize("test_engine", [True], indirect=True, ids=["pre-marketing-rows"])
def test_migrated_null_type_campaigns_keep_legacy_generation(client, test_engine, provider):
    for campaign_id, domain in ((1, "traffic_safety"), (2, "marketing")):
        url = f"{CAMPAIGNS}/{campaign_id}"
        fetched = client.get(url)
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["domain"] == domain
        assert "campaign_type" not in fetched.json()
        missing = client.post(f"{url}/generate-text", json={})
        assert missing.status_code == 422
        assert missing.json()["detail"][0]["loc"] == ["body", "audience"]

    audience = {"audience": "Drivers and passengers in Egypt"}
    unsupported = client.post(f"{CAMPAIGNS}/2/generate-text", json=audience)
    assert unsupported.status_code == 422
    assert unsupported.json() == {"detail": "Text generation currently supports traffic_safety only"}
    assert provider.calls == []
    assert client.get(f"{CAMPAIGNS}/2/contents").json() == []

    legacy = client.post(f"{CAMPAIGNS}/1/generate-text", json=audience)
    assert legacy.status_code == 201, legacy.text
    assert len(provider.calls) == 1
    _, inputs, languages = provider.calls[0]
    assert languages == {"arabic", "english"}
    assert "campaign_type" not in inputs
    for row in legacy.json()["contents"]:
        assert row["prompt_version"] == "traffic-text-v2-sourced"
        assert row["review_status"] == "draft"
        assert row["source_references"] == inputs["source_material"]
        assert row["source_references"][0]["id"] == "who-seat-belts"
        assert row["input_snapshot"]["audience"] == audience["audience"]
        assert client.get(f"{CONTENTS}/{row['id']}").json() == row
    assert {row.campaign_id for row in persisted_contents(test_engine).values()} == {1}
    with Session(test_engine) as session:
        assert session.scalars(
            select(Campaign.campaign_type).order_by(Campaign.id)
        ).all() == [None, None]
