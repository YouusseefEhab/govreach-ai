"""Read model availability without generating content or displaying credentials."""

from google import genai
from google.genai import types

from app.core.config import settings


def main():
    key = settings.gemini_api_key.get_secret_value().strip()
    if not key:
        print("GEMINI_API_KEY is not configured")
        return 1
    try:
        with genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=15000, retry_options=types.HttpRetryOptions(attempts=0),
        )) as client:
            model = client.models.get(model=settings.gemini_model)
            print("Configured model available:", model.name)
            print("Supported actions:", model.supported_actions)
            names = [item.name for item in client.models.list() if item.name and "flash" in item.name]
            print("Available Flash models:", ", ".join(names))
    except Exception as exc:
        status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        print("Model check failed:", type(exc).__name__, "HTTP", status if isinstance(status, int) else "unknown")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
