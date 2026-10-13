from uuid import uuid4

import pytest

from app.schemas.generation import TextPackage
from scripts.evaluate_text_generation import validate_capture


def body():
    generation_id = str(uuid4())
    return {
        "campaign_id": 1,
        "contents": [
            {
                "id": index + 1, "campaign_id": 1, "generation_id": generation_id,
                "language": language, "content_type": "text_package", "review_status": "draft",
                "content": {field: "Test draft" for field in TextPackage.model_fields},
                "provider": "fake", "model": "test-model", "prompt_version": "traffic-text-v2-sourced",
                "input_snapshot": {}, "source_references": [{"id": "who-seat-belts"}],
                "created_at": "2026-10-13T00:00:00Z",
            } for index, language in enumerate(["arabic", "english"])
        ],
    }


def test_valid_capture():
    result = validate_capture(body(), {"expected_source_ids": ["who-seat-belts"]})
    assert len(result.contents) == 2


@pytest.mark.parametrize("problem", ["missing_language", "split_generation", "wrong_source", "wrong_campaign", "approved"])
def test_capture_rejects_inconsistent_evidence(problem):
    data = body()
    if problem == "missing_language":
        data["contents"].pop()
    elif problem == "split_generation":
        data["contents"][1]["generation_id"] = str(uuid4())
    elif problem == "wrong_source":
        data["contents"][1]["source_references"] = [{"id": "different-source"}]
    elif problem == "wrong_campaign":
        data["contents"][1]["campaign_id"] = 2
    else:
        data["contents"][1]["review_status"] = "approved"
    with pytest.raises(AssertionError):
        validate_capture(data, {"expected_source_ids": ["who-seat-belts"]})
