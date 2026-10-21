"""Local reconciliation. Applying changes requires an offline maintenance window."""

from datetime import datetime, timezone
import time

from sqlalchemy import select, update

from app.models.image_generation import ImageGeneration
from app.services.image_library import read_verified
from app.services.image_generation import ImageRequestError
from app.storage.images import ImageStorageError, LocalImageStorage


def reconcile(db, storage: LocalImageStorage, *, apply=False, offline=False,
              min_age_hours=24, mark_unknown_id=None):
    if min_age_hours < 1:
        raise ValueError("Minimum age must be at least one hour")
    if (apply or mark_unknown_id is not None) and not offline:
        raise ValueError("Stop all API/diagnostic processes and confirm --offline before applying maintenance")
    cutoff = time.time() - min_age_hours * 3600
    rows = list(db.scalars(select(ImageGeneration)))
    referenced = {row.storage_key for row in rows if row.storage_key}
    report = {"orphans": [], "removed": [], "unavailable_images": [], "pending_requests": [], "marked_unknown": []}
    for row in rows:
        if row.request_state == "ready":
            try:
                read_verified(row, storage)
            except ImageRequestError:
                report["unavailable_images"].append(row.id)
        elif row.request_state in {"reserved", "generating", "outcome_unknown"}:
            report["pending_requests"].append({"id": row.id, "state": row.request_state})
    if mark_unknown_id is not None:
        # Explicit recovery never reclaims/retries a provider call. Offline only:
        # a request could otherwise still be actively generating in another process.
        updated = db.execute(update(ImageGeneration).where(
            ImageGeneration.id == mark_unknown_id,
            ImageGeneration.request_state == "generating",
            ImageGeneration.updated_at < datetime.fromtimestamp(cutoff, timezone.utc),
        ).values(request_state="outcome_unknown", failure_code="interrupted_request",
                 updated_at=datetime.now(timezone.utc)).execution_options(synchronize_session="fetch"))
        db.commit()
        if updated.rowcount:
            report["marked_unknown"].append(mark_unknown_id)
    if storage.root.exists():
        for path in storage.root.iterdir():
            # Never traverse directories, symlinks, or unrecognised files.
            if path.is_symlink() or not path.is_file() or not storage.key_pattern.fullmatch(path.name):
                continue
            if path.name in referenced or path.stat().st_mtime >= cutoff:
                continue
            report["orphans"].append(path.name)
            if apply:
                # Recheck the database before each deletion; DB errors abort cleanup.
                exists = db.scalar(select(ImageGeneration.id).where(ImageGeneration.storage_key == path.name).limit(1))
                if exists is None:
                    try:
                        if storage.delete(path.name):
                            report["removed"].append(path.name)
                    except ImageStorageError:
                        pass  # Still reported as an orphan, retry on the next run.
    return report
