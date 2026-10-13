import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.providers import gemini
from scripts import check_gemini


def sample():
    package = {
        "headline": "اربط حزامك", "slogan": "في كل مشوار",
        "awareness_message": "اربط الحزام قبل ما تتحرك.",
        "social_caption": "خلي الحزام عادة.", "call_to_action": "اربط حزامك.",
    }
    return {"arabic": package, "english": {name: "Buckle up." for name in package}}


def test_missing_key_never_calls_provider(monkeypatch, capsys):
    monkeypatch.setattr(check_gemini.settings, "gemini_api_key", SecretStr(""))
    client = MagicMock()
    monkeypatch.setattr(gemini.genai, "Client", client)
    assert check_gemini.main() == 1
    client.assert_not_called()
    assert "GEMINI_API_KEY" in capsys.readouterr().out


def test_live_request_contract_without_network(monkeypatch):
    monkeypatch.setattr(check_gemini.settings, "gemini_api_key", SecretStr("fake-test-key"))
    factory = MagicMock()
    client = factory.return_value.__enter__.return_value
    client.models.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason="STOP")], text=json.dumps(sample()),
    )
    monkeypatch.setattr(gemini.genai, "Client", factory)
    result = check_gemini.generate_sample()
    assert result.arabic.headline == "اربط حزامك"
    client.models.generate_content.assert_called_once()
    request = client.models.generate_content.call_args.kwargs
    assert "Egyptian Arabic" in request["config"].system_instruction
    assert request["config"].response_mime_type == "application/json"
    assert factory.call_args.kwargs["http_options"].retry_options.attempts == 0


def test_invalid_output_is_reported(monkeypatch, capsys):
    def invalid():
        return check_gemini.SampleOutput.model_validate_json('{"arabic": {}}')

    monkeypatch.setattr(check_gemini, "generate_sample", invalid)
    assert check_gemini.main() == 1
    assert "failed validation" in capsys.readouterr().out


def test_provider_exception_details_are_not_printed(monkeypatch, capsys):
    def fail():
        raise RuntimeError("private-key-provider-error-body")

    monkeypatch.setattr(check_gemini, "generate_sample", fail)
    assert check_gemini.main() == 1
    output = capsys.readouterr().out
    assert "request failed" in output
    assert "private-key" not in output


def test_gemini_secret_is_masked():
    config = Settings(_env_file=None, database_url="sqlite://", redis_url="redis://localhost", jwt_secret="test", gemini_api_key="fake-secret")
    assert "fake-secret" not in repr(config)
    assert "fake-secret" not in config.model_dump_json()


@pytest.mark.parametrize("status,expected", [
    (401, "API key"), (403, "permissions"), (404, "GEMINI_MODEL"),
    (429, "Quota or rate limit"), (503, "service is unavailable"),
])
def test_provider_status_guidance(monkeypatch, capsys, status, expected):
    def fail():
        error = RuntimeError("private-provider-body")
        error.status_code = status
        raise error

    monkeypatch.setattr(check_gemini, "generate_sample", fail)
    assert check_gemini.main() == 1
    message = capsys.readouterr().out
    assert expected in message
    assert "private-provider-body" not in message
