import logging

import httpx
from google import genai
from google.genai import types
from pydantic import ConfigDict, ValidationError, create_model

from app.core.config import settings
from app.providers.text import GenerationError
from app.schemas.generation import OutputLanguage, TextPackage

logger = logging.getLogger(__name__)


class GeminiTextProvider:
    provider_name = "gemini"

    def __init__(self):
        self.model = settings.gemini_model
        self.timeout = settings.gemini_timeout_seconds

    def generate(
        self, system_instruction: str, input_data: str, languages: set[OutputLanguage],
    ) -> dict[OutputLanguage, TextPackage]:
        key = settings.gemini_api_key.get_secret_value().strip()
        if not key or key in {"your_key_here", "YOUR_API_KEY"}:
            raise GenerationError(503, "Gemini is not configured")
        # Required fields match the campaign: never accept a partial bilingual result.
        output_schema = create_model(
            "GeminiTextPackages", __config__=ConfigDict(extra="forbid"),
            **{language: (TextPackage, ...) for language in sorted(languages)},
        )
        try:
            with genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    timeout=int(self.timeout * 1000),
                    retry_options=types.HttpRetryOptions(attempts=0),
                ),
            ) as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=input_data,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        max_output_tokens=3000,
                        response_mime_type="application/json",
                        response_json_schema=output_schema.model_json_schema(),
                        thinking_config=types.ThinkingConfig(thinking_level="low"),
                    ),
                )
            if (not response.candidates or response.candidates[0].finish_reason != "STOP"
                    or not response.text):
                raise GenerationError(502, "Gemini returned incomplete content")
            parsed = output_schema.model_validate_json(response.text)
            return {language: getattr(parsed, language) for language in sorted(languages)}
        except GenerationError:
            raise
        except ValidationError:
            raise GenerationError(502, "Gemini returned invalid content") from None
        except (TimeoutError, httpx.TimeoutException):
            raise GenerationError(504, "Gemini request timed out") from None
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            if not isinstance(status, int):
                status = getattr(exc, "code", None)
            logger.warning(
                "Gemini request failed: exception=%s, http_status=%s",
                type(exc).__name__, status if isinstance(status, int) else "unknown",
            )
            if status == 429:
                raise GenerationError(503, "Gemini quota or rate limit reached; try again later") from None
            if status in {408, 504}:
                raise GenerationError(504, "Gemini request timed out") from None
            if status in {401, 403, 404}:
                raise GenerationError(503, "Gemini credentials or model access need checking") from None
            raise GenerationError(503, "Gemini is unavailable; try again later") from None


def get_text_provider() -> GeminiTextProvider:
    """FastAPI dependency; replace with a fake provider in tests."""
    return GeminiTextProvider()
