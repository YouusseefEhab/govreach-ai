import json

import pytest
from pydantic import ValidationError

from app.services import traffic_sources


@pytest.mark.parametrize("text,expected", [
    ("حزامك أمانك في كل مشوار", {"who-seat-belts"}),
    ("Use seat belts", {"who-seat-belts"}),
    ("Buckle up", {"who-seat-belts"}),
    ("Reduce speeding", {"who-speeding"}),
    ("قلل السرعة", {"who-speeding"}),
    ("Avoid mobile phones", {"who-distracted-driving"}),
    ("سيب الموبايل وانت سايق", {"who-distracted-driving"}),
    ("Seat belts and mobile phones", {"who-seat-belts", "who-distracted-driving"}),
    ("General awareness", {"who-road-safety-general"}),
])
def test_topic_selection(text, expected):
    references = traffic_sources.select_sources("Campaign", text)
    assert {reference["id"] for reference in references} == expected
    assert all(reference["catalogue_version"] == "traffic-sources-v1" for reference in references)
    assert all(reference["usage"] == "supplied_to_generation_prompt" for reference in references)
    assert all(reference["url"].startswith("https://www.who.int/") for reference in references)
    assert all(reference["facts"] for reference in references)
    assert all("keywords" not in reference for reference in references)


@pytest.mark.parametrize("change", [
    {"url": "https://example.com/unreviewed"}, {"url": "http://www.who.int/"},
    {"facts": []}, {"keywords": []}, {"checked_on": "invalid"},
])
def test_catalogue_rejects_invalid_sources(change):
    data = json.loads(traffic_sources.CATALOGUE_PATH.read_text(encoding="utf-8"))
    data["sources"][0].update(change)
    with pytest.raises(ValidationError):
        traffic_sources.SourceCatalogue.model_validate(data)


def test_duplicate_source_ids_are_rejected():
    data = json.loads(traffic_sources.CATALOGUE_PATH.read_text(encoding="utf-8"))
    data["sources"].append(data["sources"][0])
    with pytest.raises(ValidationError):
        traffic_sources.SourceCatalogue.model_validate(data)


def test_source_reference_is_a_snapshot(tmp_path, monkeypatch):
    copied = tmp_path / "sources.json"
    original = traffic_sources.CATALOGUE_PATH.read_text(encoding="utf-8")
    copied.write_text(original, encoding="utf-8")
    monkeypatch.setattr(traffic_sources, "CATALOGUE_PATH", copied)
    selected = traffic_sources.select_sources("Seat belts", "Wear a seat belt")
    data = json.loads(original)
    data["sources"][0]["facts"] = ["Updated curated summary"]
    data["version"] = "traffic-sources-v2"
    copied.write_text(json.dumps(data), encoding="utf-8")
    assert selected[0]["catalogue_version"] == "traffic-sources-v1"
    assert selected[0]["facts"] != ["Updated curated summary"]
