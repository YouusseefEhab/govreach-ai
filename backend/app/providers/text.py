from typing import Protocol

from app.schemas.generation import OutputLanguage, TextPackage


class GenerationError(Exception):
    """Safe client-facing error, without provider bodies or credentials."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class TextProvider(Protocol):
    provider_name: str
    model: str

    def generate(
        self, system_instruction: str, input_data: str, languages: set[OutputLanguage],
    ) -> dict[OutputLanguage, TextPackage]: ...
