import json

import pytest
from app.main import app
from app.models.generated_content import GeneratedContent
from app.providers.gemini import get_text_provider
from app.providers.text import GenerationError
from app.schemas.generation import TextPackage


class FakeProvider:
    provider_name = "fake"
    model = "test-model"

    def __init__(self):
        self.calls = []
        self.error = None
        self.result = None

    def generate(self, instructions, input_data, languages):
        self.calls.append((instructions, json.loads(input_data), languages))
        if self.error:
            raise self.error
        if self.result is not None:
            return self.result
        return {
            language: TextPackage(**{
                field: "اربط حزامك قبل ما تتحرك." if language == "arabic" else "Buckle up before setting off."
                for field in TextPackage.model_fields
            }) for language in languages
        }


@pytest.fixture
def provider():
    fake = FakeProvider()
    app.dependency_overrides[get_text_provider] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_text_provider, None)


def campaign(client, **changes):
    response = client.post("/api/v1/campaigns", json={
        "title": "Seat belts", "objective": "Encourage seat belt use",
        "language": "both", **changes,
    })
    assert response.status_code == 201
    return response.json()["id"]


def generate(client, campaign_id, **changes):
    return client.post(f"/api/v1/campaigns/{campaign_id}/generate-text", json={
        "audience": "Drivers and passengers in Egypt", "tone": "informative", **changes,
    })


@pytest.mark.parametrize("language", ["arabic", "english", "both"])
def test_generation_and_retrieval(client, provider, language):
    campaign_id = campaign(client, language=language)
    response = generate(client, campaign_id)
    assert response.status_code == 201, response.text
    body = response.json()
    expected = {"arabic", "english"} if language == "both" else {language}
    assert body["campaign_id"] == campaign_id
    assert {row["language"] for row in body["contents"]} == expected
    assert len({row["generation_id"] for row in body["contents"]}) == 1
    for row in body["contents"]:
        assert row["review_status"] == "draft"
        assert row["prompt_version"] == "traffic-text-v2-sourced"
        assert row["source_references"][0]["id"] == "who-seat-belts"
        assert row["source_references"] == provider.calls[0][1]["source_material"]
        assert row["input_snapshot"]["arabic_dialect"] == "egyptian"
        assert client.get(f"/api/v1/contents/{row['id']}").json() == row
    history = client.get(f"/api/v1/campaigns/{campaign_id}/contents").json()
    assert {row["id"] for row in history} == {row["id"] for row in body["contents"]}
    assert provider.calls[0][2] == expected
    assert "Egyptian Arabic" in provider.calls[0][0]
    assert client.get(f"/api/v1/campaigns/{campaign_id}").json()["status"] == "draft"


def test_history_pagination_and_cascade(client, provider):
    campaign_id = campaign(client)
    first = generate(client, campaign_id).json()["contents"]
    second = generate(client, campaign_id).json()["contents"]
    assert first[0]["generation_id"] != second[0]["generation_id"]
    history = client.get(f"/api/v1/campaigns/{campaign_id}/contents").json()
    assert len(history) == 4
    page = client.get(f"/api/v1/campaigns/{campaign_id}/contents?skip=1&limit=1").json()
    assert page == history[1:2]
    assert client.delete(f"/api/v1/campaigns/{campaign_id}").status_code == 204
    assert client.get(f"/api/v1/contents/{first[0]['id']}").status_code == 404
    assert client.get(f"/api/v1/campaigns/{campaign_id}/contents").status_code == 404


@pytest.mark.parametrize("status", [502, 503, 504])
def test_provider_failure_preserves_history(client, provider, status):
    campaign_id = campaign(client)
    generate(client, campaign_id)
    before = client.get(f"/api/v1/campaigns/{campaign_id}/contents").json()
    provider.error = GenerationError(status, "Safe provider error")
    response = generate(client, campaign_id)
    assert response.status_code == status
    assert response.json() == {"detail": "Safe provider error"}
    assert client.get(f"/api/v1/campaigns/{campaign_id}/contents").json() == before


@pytest.mark.parametrize("result", [{}, {"arabic": {}}, {"arabic": {}, "english": {}}])
def test_bad_provider_output_never_saved(client, provider, result):
    campaign_id = campaign(client)
    provider.result = result
    assert generate(client, campaign_id).status_code == 502
    assert client.get(f"/api/v1/campaigns/{campaign_id}/contents").json() == []


def test_campaign_checks_precede_provider(client, provider):
    assert generate(client, 999999).status_code == 404
    campaign_id = campaign(client, domain="other")
    assert generate(client, campaign_id).status_code == 422
    assert provider.calls == []


@pytest.mark.parametrize("body", [
    {}, {"audience": " "}, {"audience": "x" * 301},
    {"audience": "Drivers", "tone": "sarcastic"},
    {"audience": "Drivers", "language": "arabic"},
])
def test_bad_request_never_calls_provider(client, provider, body):
    campaign_id = campaign(client)
    response = client.post(f"/api/v1/campaigns/{campaign_id}/generate-text", json=body)
    assert response.status_code == 422
    assert provider.calls == []


def test_missing_key_returns_controlled_error(client):
    campaign_id = campaign(client)
    response = generate(client, campaign_id)
    assert response.status_code == 503
    assert response.json() == {"detail": "Gemini is not configured"}
    assert client.get(f"/api/v1/campaigns/{campaign_id}/contents").json() == []


def test_retrieval_is_campaign_scoped(client, provider):
    first = campaign(client)
    second = campaign(client)
    generate(client, first)
    assert client.get(f"/api/v1/campaigns/{second}/contents").json() == []
    assert client.get("/api/v1/contents/999999").status_code == 404


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101"])
def test_retrieval_pagination_validation(client, query):
    campaign_id = campaign(client)
    assert client.get(f"/api/v1/campaigns/{campaign_id}/contents?{query}").status_code == 422


def test_reviewed_content_can_be_retrieved(client, provider, db):
    campaign_id = campaign(client)
    result = generate(client, campaign_id).json()
    row = db.get(GeneratedContent, result["contents"][0]["id"])
    row.review_status = "approved"
    db.commit()
    assert client.get(f"/api/v1/contents/{row.id}").json()["review_status"] == "approved"


def test_new_routes_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths["/api/v1/campaigns/{campaign_id}/generate-text"]
    assert "get" in paths["/api/v1/campaigns/{campaign_id}/contents"]
    assert "get" in paths["/api/v1/contents/{content_id}"]


def test_storage_failure_is_controlled_and_preserves_history(client, provider):
    campaign_id = campaign(client)
    generate(client, campaign_id)
    before = client.get(f"/api/v1/campaigns/{campaign_id}/contents").json()
    provider.model = None  # Force the database's non-null metadata constraint.
    response = generate(client, campaign_id)
    assert response.status_code == 503
    assert response.json()["detail"].startswith("Generated content could not be saved")
    assert client.get(f"/api/v1/campaigns/{campaign_id}/contents").json() == before
    provider.model = "test-model"
    assert generate(client, campaign_id).status_code == 201


def test_partial_edit_preserves_other_fields_versions_and_metadata(client, provider):
    campaign_id = campaign(client)
    first = generate(client, campaign_id).json()["contents"]
    second = generate(client, campaign_id).json()["contents"]
    arabic = next(row for row in first if row["language"] == "arabic")
    url = f"/api/v1/contents/{arabic['id']}"
    response = client.patch(url, json={"content": {"awareness_message": "خلي ربط الحزام عادة في كل مشوار."}})
    assert response.status_code == 200
    updated = response.json()
    assert updated["content"]["awareness_message"] == "خلي ربط الحزام عادة في كل مشوار."
    for field in arabic["content"]:
        if field != "awareness_message":
            assert updated["content"][field] == arabic["content"][field]
    for field in arabic:
        if field != "content":
            assert updated[field] == arabic[field]
    for row in first + second:
        if row["id"] != arabic["id"]:
            assert client.get(f"/api/v1/contents/{row['id']}").json() == row
    assert client.get(url).json() == updated
    assert len(provider.calls) == 2  # Editing consumes no provider request.


@pytest.mark.parametrize("status", ["approved", "rejected", "draft"])
def test_review_status_and_reedit_reset(client, provider, status):
    campaign_id = campaign(client)
    row = generate(client, campaign_id).json()["contents"][0]
    url = f"/api/v1/contents/{row['id']}"
    reviewed = client.patch(url, json={"review_status": status})
    assert reviewed.status_code == 200
    assert reviewed.json()["review_status"] == status
    assert reviewed.json()["content"] == row["content"]
    assert client.get(f"/api/v1/campaigns/{campaign_id}").json()["status"] == "draft"
    edited = client.patch(url, json={"content": {"headline": "  عنوان جديد  "}})
    assert edited.status_code == 200
    assert edited.json()["review_status"] == "draft"
    assert edited.json()["content"]["headline"] == "عنوان جديد"
    assert len(provider.calls) == 1


@pytest.mark.parametrize("body", [
    {}, {"content": {}}, {"content": None}, {"review_status": None},
    {"content": {"headline": None}}, {"content": {"headline": " "}},
    {"content": {"headline": "x" * 121}}, {"content": {"unknown": "value"}},
    {"review_status": "published"}, {"language": "english"},
    {"campaign_id": 999999}, {"model": "different"},
    {"content": {"headline": "Changed"}, "review_status": "approved"},
    {"content": {"headline": "Changed"}, "review_status": "rejected"},
])
def test_invalid_edit_preserves_saved_record(client, provider, body):
    campaign_id = campaign(client)
    row = generate(client, campaign_id).json()["contents"][0]
    url = f"/api/v1/contents/{row['id']}"
    assert client.patch(url, json=body).status_code == 422
    assert client.get(url).json() == row


def test_missing_content_update(client):
    response = client.patch("/api/v1/contents/999999", json={"review_status": "approved"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Generated content not found"}


def test_edit_commit_failure_rolls_back(client, provider, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session

    campaign_id = campaign(client)
    row = generate(client, campaign_id).json()["contents"][0]
    url = f"/api/v1/contents/{row['id']}"

    def fail_commit(self):
        raise SQLAlchemyError("Simulated database failure")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        response = client.patch(url, json={"content": {"headline": "Must not be saved"}})
    assert response.status_code == 503
    assert client.get(url).json() == row
    assert client.patch(url, json={"review_status": "approved"}).status_code == 200


def test_missing_source_catalogue_prevents_provider_call(client, provider, monkeypatch):
    from app.services import generation

    campaign_id = campaign(client)

    def unavailable(*args):
        raise OSError("Catalogue missing")

    monkeypatch.setattr(generation, "select_sources", unavailable)
    response = generate(client, campaign_id)
    assert response.status_code == 503
    assert "source catalogue" in response.json()["detail"]
    assert provider.calls == []
    assert client.get(f"/api/v1/campaigns/{campaign_id}/contents").json() == []


def test_saved_sources_preserved_after_edit(client, provider):
    campaign_id = campaign(client)
    row = generate(client, campaign_id).json()["contents"][0]
    response = client.patch(f"/api/v1/contents/{row['id']}", json={"content": {"headline": "Edited"}})
    assert response.status_code == 200
    assert response.json()["source_references"] == row["source_references"]
    assert response.json()["review_status"] == "draft"
