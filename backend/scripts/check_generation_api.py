"""PostgreSQL API check. --live makes one Gemini call; all test rows roll back."""

import argparse
import sys

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models import Campaign, GeneratedContent
from app.providers.gemini import get_text_provider
from app.schemas.generation import TextPackage


class FakeProvider:
    provider_name = "fake"
    model = "api-check"

    def generate(self, system_instruction, input_data, languages):
        return {
            language: TextPackage(**{
                field: "اربط الحزام قبل ما تتحرك." if language == "arabic" else "Buckle up before setting off."
                for field in TextPackage.model_fields
            }) for language in languages
        }


def row_counts(connection):
    return tuple(connection.execute(select(func.count()).select_from(model)).scalar()
                 for model in (Campaign, GeneratedContent))


def check_api(live=False):
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Use the configured PostgreSQL database for this diagnostic")
    previous = app.dependency_overrides.copy()
    with engine.connect() as connection:
        outer = connection.begin()
        before = row_counts(connection)

        def diagnostic_db():
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                yield session

        app.dependency_overrides[get_db] = diagnostic_db
        if not live:
            app.dependency_overrides[get_text_provider] = lambda: FakeProvider()
        try:
            with TestClient(app) as client:
                created = client.post("/api/v1/campaigns", json={
                    "title": "Seat belt API diagnostic (rolled back)",
                    "objective": "Encourage drivers and passengers to wear seat belts before every trip",
                    "language": "both",
                })
                assert created.status_code == 201
                campaign_id = created.json()["id"]
                response = client.post(f"/api/v1/campaigns/{campaign_id}/generate-text", json={
                    "audience": "Drivers and passengers in Egypt", "tone": "informative",
                })
                if response.status_code != 201:
                    # API details are sanitized by the generation routes/provider.
                    print(f"Generation returned HTTP {response.status_code}: {response.json().get('detail')}")
                    return 1
                body = response.json()
                assert {row["language"] for row in body["contents"]} == {"arabic", "english"}
                assert len({row["generation_id"] for row in body["contents"]}) == 1
                for row in body["contents"]:
                    assert row["review_status"] == "draft"
                    assert row["prompt_version"] == "traffic-text-v2-sourced"
                    assert row["source_references"][0]["id"] == "who-seat-belts"
                    assert row["source_references"][0]["catalogue_version"] == "traffic-sources-v1"
                    assert client.get(f"/api/v1/contents/{row['id']}").json() == row
                    print(f"{row['language']} headline: {row['content']['headline']}")
                history = client.get(f"/api/v1/campaigns/{campaign_id}/contents")
                assert history.status_code == 200 and len(history.json()) == 2
                arabic = next(row for row in body["contents"] if row["language"] == "arabic")
                english = next(row for row in body["contents"] if row["language"] == "english")
                content_url = f"/api/v1/contents/{arabic['id']}"
                edited = client.patch(content_url, json={"content": {
                    "awareness_message": "خلي ربط الحزام عادة في كل مشوار.",
                }})
                assert edited.status_code == 200
                assert edited.json()["content"]["awareness_message"] == "خلي ربط الحزام عادة في كل مشوار."
                assert edited.json()["content"]["headline"] == arabic["content"]["headline"]
                assert edited.json()["generation_id"] == arabic["generation_id"]
                for review_status in ("approved", "rejected"):
                    reviewed = client.patch(content_url, json={"review_status": review_status})
                    assert reviewed.status_code == 200
                    assert reviewed.json()["review_status"] == review_status
                    assert client.get(content_url).json()["review_status"] == review_status
                redrafted = client.patch(content_url, json={"content": {"headline": "حزامك أمانك في كل مشوار"}})
                assert redrafted.status_code == 200 and redrafted.json()["review_status"] == "draft"
                assert client.get(f"/api/v1/contents/{english['id']}").json() == english
                assert client.get(f"/api/v1/campaigns/{campaign_id}").json()["status"] == "draft"
                assert client.delete(f"/api/v1/campaigns/{campaign_id}").status_code == 204
                assert client.get(f"/api/v1/contents/{body['contents'][0]['id']}").status_code == 404
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
            outer.rollback()
            assert row_counts(connection) == before
            print("Diagnostic database changes rolled back; existing row counts unchanged.")
    print("PostgreSQL API checks passed: generation 201; retrieval, editing, and review 200; cascade deletion 204/404.")
    print("All diagnostic rows were rolled back. Existing rows remain intact.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Use Gemini instead of a fake provider; consumes one request")
    parser.add_argument("--model", help="Override the model for this diagnostic only")
    args = parser.parse_args()
    if args.model:
        settings.gemini_model = args.model
    try:
        result = check_api(live=args.live)
    except Exception:
        print("Generation API diagnostic failed. Check PostgreSQL, migrations, and application configuration.")
        result = 1
    finally:
        engine.dispose()
    raise SystemExit(result)
