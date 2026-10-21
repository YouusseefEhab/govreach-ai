"""Decode and verify bounded, single-frame square PNG/JPEG outputs."""

from dataclasses import dataclass
from io import BytesIO
import warnings
import struct

from PIL import Image, UnidentifiedImageError

from app.providers.image import ImageOutput


class InvalidImageError(Exception):
    pass


@dataclass(frozen=True)
class ValidatedImage:
    data: bytes
    mime_type: str
    width: int
    height: int


def validate_image(output: ImageOutput, *, max_bytes: int = 10 * 1024 * 1024,
                   max_edge: int = 2048, max_pixels: int = 2048 * 2048) -> ValidatedImage:
    if not isinstance(output, ImageOutput) or not isinstance(output.data, bytes):
        raise InvalidImageError("Provider returned an invalid image object")
    if not output.data or len(output.data) > max_bytes or not isinstance(output.mime_type, str) or output.mime_type not in {"image/png", "image/jpeg"}:
        raise InvalidImageError("Invalid image size or media type")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(output.data), formats=["PNG", "JPEG"]) as image:
                width, height = image.size
                detected = {"PNG": "image/png", "JPEG": "image/jpeg"}.get(image.format)
                if detected != output.mime_type:
                    raise InvalidImageError("Image media type does not match its bytes")
                if width != height or min(width, height) < 1 or max(width, height) > max_edge or width * height > max_pixels:
                    raise InvalidImageError("Image dimensions exceed the square-image limits")
                if getattr(image, "n_frames", 1) != 1:
                    raise InvalidImageError("Animated images are unsupported")
                image.verify()
            # verify() does not decode pixels. Reopen and fully load as well.
            with Image.open(BytesIO(output.data), formats=["PNG", "JPEG"]) as image:
                image.load()
        return ValidatedImage(output.data, output.mime_type, width, height)
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, struct.error,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise InvalidImageError("Image bytes failed verification") from None
