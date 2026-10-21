import base64
from io import BytesIO
import json

import httpx
from PIL import Image
from pydantic import SecretStr
import pytest

from app.core.config import settings
from app.providers.cloudflare import CloudflareImageProvider, MODEL, PROMPT_VERSION, build_prompt, get_image_provider
from app.providers.image import ImageProviderError
from app.services.image_generation import generate_image
from app.services.image_validation import validate_image
from tests.test_image_pipeline import arguments


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "image_provider", "cloudflare")
    monkeypatch.setattr(settings, "cloudflare_free_plan_confirmed", True)
    monkeypatch.setattr(settings, "cloudflare_account_id", "a" * 32)
    monkeypatch.setattr(settings, "cloudflare_api_token", SecretStr("test-cloudflare-token"))


def jpeg():
    buffer = BytesIO()
    with Image.new("RGB", (32, 32), "blue") as image:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def provider(handler):
    return CloudflareImageProvider(transport=httpx.MockTransport(handler))


def test_one_fixed_model_request_decodes_documented_base64_response(configured):
    data = jpeg()
    calls = []
    def handle(request):
        calls.append(request)
        assert request.url.host == "api.cloudflare.com"
        assert str(request.url).endswith("/ai/run/" + MODEL)
        assert request.headers["Authorization"] == "Bearer test-cloudflare-token"
        body = json.loads(request.content)
        assert set(body) == {"prompt", "steps"} and body["steps"] == 4
        assert "No written text" in body["prompt"]
        return httpx.Response(200, json={"success": True, "result": {"image": base64.b64encode(data).decode()}})
    output = provider(handle).generate("A parked car with seat belts", {"content": {"headline": "Buckle up"}}, "illustration")
    assert output.data == data and output.mime_type == "image/jpeg"
    assert validate_image(output).width == 32 and len(calls) == 1


@pytest.mark.parametrize("status,expected,ambiguous", [(429, 503, False), (401, 503, False), (403, 503, False), (404, 503, False), (400, 422, False), (422, 422, False), (503, 503, True), (504, 504, True), (302, 503, True)])
def test_safe_errors_never_retry_redirect_or_fallback(configured, status, expected, ambiguous):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(status, headers={"Location": "https://untrusted.invalid"}, text="private provider response")
    with pytest.raises(ImageProviderError) as error:
        provider(handle).generate("Safe scene", {}, "illustration")
    assert error.value.status_code == expected and error.value.ambiguous == ambiguous
    assert "private" not in str(error.value) and "test-cloudflare-token" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("failure,status", [(httpx.ReadTimeout("private"), 504), (httpx.ConnectError("private"), 503)])
def test_transport_failures_are_ambiguous_and_not_retried(configured, failure, status):
    calls = []
    def handle(request):
        calls.append(request)
        raise failure
    with pytest.raises(ImageProviderError) as error:
        provider(handle).generate("Safe scene", {}, "illustration")
    assert error.value.status_code == status and error.value.ambiguous
    assert "private" not in str(error.value) and len(calls) == 1


@pytest.mark.parametrize("body", [None, [], {"success": True}, {"success": True, "result": {"image": "@@invalid@@"}}, {"success": True, "result": {"image": ""}}])
def test_malformed_results_are_rejected(configured, body):
    with pytest.raises(ImageProviderError):
        provider(lambda request: httpx.Response(200, json=body)).generate("Safe scene", {}, "illustration")


def test_response_size_and_prompt_limits_fail_without_extra_calls(configured, monkeypatch):
    monkeypatch.setattr(settings, "media_max_bytes", 10)
    with pytest.raises(ImageProviderError, match="invalid image"):
        provider(lambda request: httpx.Response(200, json={"success": True, "result": {"image": "A" * 100}})).generate("Scene", {}, "illustration")
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(500)
    with pytest.raises(ImageProviderError, match="shorten"):
        provider(handle).generate("x" * 2048, {}, "illustration")
    assert calls == []


@pytest.mark.parametrize("field,value", [("image_provider", "fake"), ("cloudflare_free_plan_confirmed", False), ("cloudflare_account_id", "../bad"), ("cloudflare_api_token", SecretStr(""))])
def test_configuration_gate_prevents_network_calls(configured, monkeypatch, field, value):
    monkeypatch.setattr(settings, field, value)
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(500)
    with pytest.raises(ImageProviderError):
        provider(handle).generate("Scene", {}, "illustration")
    assert calls == []


def test_factory_defaults_to_fake_and_requires_free_plan_confirmation(monkeypatch):
    assert get_image_provider().provider_name == "fake"
    monkeypatch.setattr(settings, "image_provider", "cloudflare")
    with pytest.raises(ImageProviderError):
        get_image_provider()


def test_cloudflare_pipeline_records_actual_provider_and_replays_without_second_call(configured, db, tmp_path):
    campaign, _, _, request, identity, storage = arguments(db, tmp_path)
    calls = []
    def handle(http_request):
        calls.append(http_request)
        return httpx.Response(200, json={"success": True, "result": {"image": base64.b64encode(jpeg()).decode()}})
    adapter = provider(handle)
    row, created = generate_image(db, campaign.id, request, identity, adapter, storage)
    assert created and row.provider == "cloudflare" and row.model == MODEL
    assert row.prompt_version == PROMPT_VERSION and row.mime_type == "image/jpeg"
    replay, created = generate_image(db, campaign.id, request, identity, adapter, storage)
    assert not created and replay.id == row.id and len(calls) == 1


def test_prompt_uses_visual_reference_fields_and_does_not_silently_truncate():
    result = build_prompt("A safe crossing", {"content": {"headline": "Cross safely", "awareness_message": "long text" * 1000}}, "illustration")
    assert "Cross safely" in result and "long text" not in result
    assert "A safe crossing" in result and len(result) <= 2048
