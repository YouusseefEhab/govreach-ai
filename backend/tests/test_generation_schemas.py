import pytest
from pydantic import ValidationError

from app.schemas.generation import (
    TextGenerationRequest,
    TextGenerationResponse,
    TextPackage,
)


def package(**changes):
    return {
        "headline": "سلامتك بتبدأ بحزام الأمان",
        "slogan": "اربط الحزام في كل مشوار",
        "awareness_message": "خلّي ربط الحزام عادة ليك ولكل اللي معاك في العربية.",
        "social_caption": "قبل ما تتحرك، اتأكد إن كل اللي معاك رابطين الحزام.",
        "call_to_action": "اربط حزامك قبل ما تبدأ المشوار.",
        **changes,
    }


def output(language="arabic", **changes):
    return {"id": 1, "language": language, "content": package(), **changes}


def test_request_defaults_and_trim():
    request = TextGenerationRequest(audience="  السواقين والركاب في مصر  ")
    assert request.audience == "السواقين والركاب في مصر"
    assert request.tone == "informative"


@pytest.mark.parametrize("tone", ["informative", "encouraging", "formal"])
def test_supported_tones(tone):
    assert TextGenerationRequest(audience="Drivers", tone=tone).tone == tone


@pytest.mark.parametrize("data", [
    {}, {"audience": " \t\n "}, {"audience": "x" * 301},
    {"audience": "Drivers", "tone": "sarcastic"},
    {"audience": "Drivers", "language": "both"},
    {"audience": "Drivers", "arabic_style": "msa"},
])
def test_invalid_request(data):
    with pytest.raises(ValidationError):
        TextGenerationRequest.model_validate(data)


@pytest.mark.parametrize("field,limit", [
    ("headline", 120), ("slogan", 100), ("awareness_message", 1200),
    ("social_caption", 600), ("call_to_action", 200),
])
def test_package_field_limits(field, limit):
    assert getattr(TextPackage(**package(**{field: "x" * limit})), field) == "x" * limit
    for invalid in [" \t\n ", "x" * (limit + 1), None]:
        with pytest.raises(ValidationError):
            TextPackage(**package(**{field: invalid}))
    missing = package()
    del missing[field]
    with pytest.raises(ValidationError):
        TextPackage(**missing)


def test_package_preserves_egyptian_text_and_forbids_extra_fields():
    validated = TextPackage(**package(headline="  سلامتك بتبدأ بحزام الأمان  "))
    assert validated.headline == "سلامتك بتبدأ بحزام الأمان"
    with pytest.raises(ValidationError):
        TextPackage(**package(unexpected="value"))


@pytest.mark.parametrize("languages", [["arabic"], ["english"], ["arabic", "english"]])
def test_response_language_variants(languages):
    response = TextGenerationResponse(
        campaign_id=3,
        contents=[output(language, id=index + 1) for index, language in enumerate(languages)],
    )
    assert [item.language for item in response.contents] == languages
    assert all(item.review_status == "draft" for item in response.contents)


@pytest.mark.parametrize("contents", [
    [], [output(), output()], [output("both")],
    [output(review_status="approved")], [output(id=0)],
    [output(content_type="image")],
    [output("arabic"), output("english"), output("arabic")],
])
def test_invalid_responses(contents):
    with pytest.raises(ValidationError):
        TextGenerationResponse(campaign_id=3, contents=contents)


def test_invalid_campaign_id():
    with pytest.raises(ValidationError):
        TextGenerationResponse(campaign_id=0, contents=[output()])
