import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.providers import gemini
from app.providers.text import GenerationError


def package():
    return {field: "Buckle up." for field in gemini.TextPackage.model_fields}


@pytest.fixture
def sdk(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("fake-test-key"))
    factory = MagicMock()
    monkeypatch.setattr(gemini.genai, "Client", factory)
    return factory, factory.return_value.__enter__.return_value


@pytest.mark.parametrize("languages", [{"arabic"}, {"english"}, {"arabic", "english"}])
def test_sdk_request_contract(sdk, languages):
    factory, client = sdk
    client.models.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason="STOP")], text=json.dumps({language: package() for language in languages}),
    )
    provider = gemini.GeminiTextProvider()
    result = provider.generate("fixed instructions", '{"audience":"Drivers"}', languages)
    assert set(result) == languages
    request = client.models.generate_content.call_args.kwargs
    assert set(request["config"].response_json_schema["required"]) == languages
    assert request["config"].system_instruction == "fixed instructions"
    assert request["config"].response_mime_type == "application/json"
    assert request["config"].thinking_config.thinking_level == "LOW"
    assert factory.call_args.kwargs["http_options"].retry_options.attempts == 0
    client.models.generate_content.assert_called_once()


@pytest.mark.parametrize("output", ["not json", "{}", '{"arabic": {}}'])
def test_malformed_provider_output(sdk, output):
    _, client = sdk
    client.models.generate_content.return_value = SimpleNamespace(candidates=[SimpleNamespace(finish_reason="STOP")], text=output)
    with pytest.raises(GenerationError) as error:
        gemini.GeminiTextProvider().generate("rules", "data", {"arabic", "english"})
    assert error.value.status_code == 502


def test_incomplete_response(sdk):
    _, client = sdk
    client.models.generate_content.return_value = SimpleNamespace(candidates=[], text=None)
    with pytest.raises(GenerationError) as error:
        gemini.GeminiTextProvider().generate("rules", "data", {"arabic"})
    assert error.value.status_code == 502


@pytest.mark.parametrize("status,expected", [(401, 503), (403, 503), (404, 503), (429, 503), (503, 503), (504, 504)])
def test_sanitized_provider_errors(sdk, status, expected, caplog):
    _, client = sdk
    error = RuntimeError("private-key-response-body")
    error.status_code = status
    client.models.generate_content.side_effect = error
    with pytest.raises(GenerationError) as caught:
        gemini.GeminiTextProvider().generate("rules", "data", {"arabic"})
    assert caught.value.status_code == expected
    assert "private-key" not in caught.value.detail
    assert "private-key" not in caplog.text


def test_timeout(sdk):
    _, client = sdk
    client.models.generate_content.side_effect = httpx.ReadTimeout("private-message")
    with pytest.raises(GenerationError) as error:
        gemini.GeminiTextProvider().generate("rules", "data", {"english"})
    assert error.value.status_code == 504


def test_truncated_content_is_not_accepted(sdk):
    _, client = sdk
    client.models.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")],
        text=json.dumps({"english": package()}),
    )
    with pytest.raises(GenerationError) as error:
        gemini.GeminiTextProvider().generate("rules", "data", {"english"})
    assert error.value.status_code == 502
