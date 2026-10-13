"""Run with: python -m scripts.check_gemini. Makes one live generation request."""

import json
import sys

from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import settings
from app.providers.gemini import GeminiTextProvider
from app.schemas.generation import TextPackage


class SampleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arabic: TextPackage
    english: TextPackage


PROMPT = """Create two short draft traffic-safety text packages about wearing a
seat belt before every journey, for drivers and passengers in Egypt.
The arabic package must use natural Egyptian Arabic (العامية المصرية), not
Modern Standard Arabic. Example style: اربط الحزام في كل مشوار.
The english package must communicate the same meaning in natural English.
Use an informative, respectful public-awareness tone. Each package contains
headline, slogan, awareness_message, social_caption, and call_to_action.
Keep every field concise and within the supplied schema's character limits.
Do not invent statistics, fines, legal requirements, or government endorsement.
This is a fictional development sample for human review, not official guidance.
"""


def generate_sample() -> SampleOutput:
    key = settings.gemini_api_key.get_secret_value().strip()
    if not key or key in {"your_key_here", "YOUR_API_KEY"}:
        raise ValueError("missing_key")

    packages = GeminiTextProvider().generate(
        PROMPT, "Generate the requested seat-belt sample.", {"arabic", "english"},
    )
    return SampleOutput(**packages)


def main() -> int:
    try:
        output = generate_sample()
    except ValidationError:
        print("Gemini responded, but the text package failed validation. No content was saved.")
        return 1
    except ValueError as exc:
        if str(exc) == "missing_key":
            print("Add GEMINI_API_KEY to the project root .env, then run this command again.")
        else:
            print("Gemini did not return a complete text package. No content was saved.")
        return 1
    except Exception as exc:
        # Do not print provider exception bodies, URLs, credentials, or tracebacks.
        status = getattr(exc, "status_code", None)
        if not isinstance(status, int):
            status = getattr(exc, "code", None)
        suffix = f" (HTTP {status})" if isinstance(status, int) else ""
        guidance = {
            401: "Check your Gemini API key.",
            403: "Check API key permissions and project access.",
            404: "Check GEMINI_MODEL and whether it is available to your project.",
            429: "Quota or rate limit reached. Check AI Studio usage before trying again.",
            503: "Gemini service is unavailable. Try again later; no content was saved.",
        }.get(status, "Check the key, model access, quota, and connection.")
        print(f"Gemini request failed{suffix}. {guidance}")
        return 1

    print("Gemini connection successful. Both text packages passed structural validation.")
    print("Review Egyptian dialect, English meaning, and factual quality before use.")
    print(json.dumps(output.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
