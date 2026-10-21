"""Image-provider boundary and deterministic local test provider."""

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class ImageOutput:
    data: bytes
    mime_type: str


class ImageProviderError(Exception):
    def __init__(self, code: str, status_code: int, detail: str, *, ambiguous: bool = False):
        super().__init__(detail)
        self.code = code
        self.status_code = status_code
        self.detail = detail
        self.ambiguous = ambiguous


class ImageProvider(Protocol):
    provider_name: str
    model: str

    def generate(self, visual_brief: str, source_snapshot: dict, style: str) -> ImageOutput: ...


class FakeImageProvider:
    """Deterministic placeholder PNG, not AI artwork or a real safety illustration."""

    provider_name = "fake"
    model = "fake-image-v1"

    def generate(self, visual_brief: str, source_snapshot: dict, style: str) -> ImageOutput:
        buffer = BytesIO()
        with Image.new("RGB", (32, 32), color=(36, 89, 197)) as image:
            image.save(buffer, format="PNG")
        return ImageOutput(buffer.getvalue(), "image/png")
