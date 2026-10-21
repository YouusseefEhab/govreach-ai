"""Bounded opaque-byte storage. Image decoding/verification belongs upstream.

No provider calls, public file serving, or directory creation on module import.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Protocol
from uuid import uuid4


class ImageStorageError(Exception):
    pass


@dataclass(frozen=True)
class StoredImageFile:
    key: str
    byte_count: int
    checksum: str


class ImageStorage(Protocol):
    def put(self, data: bytes, mime_type: str) -> StoredImageFile: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> bool: ...


class LocalImageStorage:
    extensions = {"image/png": ".png", "image/jpeg": ".jpg"}
    key_pattern = re.compile(r"[a-f0-9]{32}\.(?:png|jpg)\Z")

    def __init__(self, root: Path, max_bytes: int = 10 * 1024 * 1024):
        if root.is_symlink() or max_bytes <= 0:
            raise ImageStorageError("Invalid media storage configuration")
        self.root = root.resolve()
        self.max_bytes = max_bytes

    def _path(self, key: str) -> Path:
        if not self.key_pattern.fullmatch(key):
            raise ImageStorageError("Invalid image storage key")
        path = self.root / key
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ImageStorageError("Invalid image storage key")
        return path

    def put(self, data: bytes, mime_type: str) -> StoredImageFile:
        if mime_type not in self.extensions or not data or len(data) > self.max_bytes:
            raise ImageStorageError("Invalid image byte size or media type")
        key = uuid4().hex + self.extensions[mime_type]
        path = self._path(key)
        created = False
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as file:
                created = True
                file.write(data)
            return StoredImageFile(key, len(data), hashlib.sha256(data).hexdigest())
        except OSError:
            if created:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass  # Reconciliation will handle any orphan after a failed write.
            raise ImageStorageError("Image storage write failed") from None

    def read(self, key: str) -> bytes:
        path = self._path(key)
        try:
            with path.open("rb") as file:
                data = file.read(self.max_bytes + 1)
            if not data or len(data) > self.max_bytes:
                raise ImageStorageError("Invalid stored image size")
            return data
        except OSError:
            raise ImageStorageError("Stored image is unavailable") from None

    def delete(self, key: str) -> bool:
        path = self._path(key)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False
        except OSError:
            raise ImageStorageError("Image cleanup failed") from None
