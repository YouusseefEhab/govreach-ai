"""Three-case evaluation capture. --live uses Gemini; database changes roll back."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models import Campaign, GeneratedContent
from app.providers.gemini import get_text_provider
from app.schemas.generation import SavedTextGenerationResponse
from scripts.check_generation_api import FakeProvider


EVALUATION_DIR = Path(__file__).resolve().parents[1] / "evaluation"


def validate_capture(body, case):
    """Technical checks only; this does not grade language or factual quality."""
    response = SavedTextGenerationResponse.model_validate(body)
    assert {row.language for row in response.contents} == {"arabic", "english"}
    assert len({row.generation_id for row in response.contents}) == 1
    for row in response.contents:
        assert row.campaign_id == response.campaign_id
        assert row.review_status == "draft"
        assert {reference["id"] for reference in row.source_references} == set(case["expected_source_ids"])
    return response


def evaluate(live=False):
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Configure PostgreSQL before running this diagnostic")
    cases = json.loads((EVALUATION_DIR / "cases.json").read_text(encoding="utf-8"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = EVALUATION_DIR / "runs" / f"{run_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run_id, "mode": "live" if live else "fake",
        "configured_model": settings.gemini_model,
        "quality_review": "pending; technical checks are not quality scores",
        "cases": [], "database_cleanup": "pending",
        "token_usage_and_cost": "not measured by this capture",
    }

    def save_report():
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    previous = app.dependency_overrides.copy()
    with engine.connect() as connection:
        outer = connection.begin()
        initial_counts = [connection.execute(select(func.count()).select_from(model)).scalar()
                          for model in (Campaign, GeneratedContent)]

        def diagnostic_db():
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                yield db

        app.dependency_overrides[get_db] = diagnostic_db
        if not live:
            app.dependency_overrides[get_text_provider] = lambda: FakeProvider()
        try:
            with TestClient(app) as client:
                for case in cases:
                    entry = {"case_id": case["case_id"], "inputs": case, "technical_checks": "pending"}
                    report["cases"].append(entry)
                    try:
                        created = client.post("/api/v1/campaigns", json=case["campaign"])
                        assert created.status_code == 201
                        campaign_id = created.json()["id"]
                        started = perf_counter()
                        response = client.post(f"/api/v1/campaigns/{campaign_id}/generate-text", json=case["request"])
                        entry["latency_seconds"] = round(perf_counter() - started, 2)
                        entry["http_status"] = response.status_code
                        entry["response"] = response.json()
                        if response.status_code == 201:
                            validated = validate_capture(entry["response"], case)
                            for row in validated.contents:
                                retrieved = client.get(f"/api/v1/contents/{row.id}")
                                assert retrieved.status_code == 200
                                assert retrieved.json() == next(item for item in entry["response"]["contents"] if item["id"] == row.id)
                            entry["technical_checks"] = "passed"
                        else:
                            entry["technical_checks"] = "generation_failed"
                    except Exception as exc:
                        # Type only: never record credentials, URLs with keys, or provider bodies.
                        entry["technical_checks"] = "failed"
                        entry["error_type"] = type(exc).__name__
                    save_report()
                    print(f"{case['case_id']}: HTTP {entry.get('http_status', 'unknown')}, {entry['technical_checks']}", flush=True)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
            outer.rollback()
            final_counts = [connection.execute(select(func.count()).select_from(model)).scalar()
                            for model in (Campaign, GeneratedContent)]
            report["database_cleanup"] = "rolled back; row counts unchanged" if initial_counts == final_counts else "rolled back; counts changed during evaluation"
            save_report()
    print("Evaluation capture:", output_path, flush=True)
    print("Temporary database records rolled back; captured IDs are not persistent API IDs.", flush=True)
    return output_path


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Make three sequential provider requests, with no retries")
    args = parser.parse_args()
    try:
        evaluate(live=args.live)
    except Exception as exc:
        print("Evaluation could not complete:", type(exc).__name__)
        raise SystemExit(1)
    finally:
        engine.dispose()
