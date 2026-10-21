"""Image request identity and metadata, separate from text packages."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImageGeneration(Base):
    __tablename__ = "image_generations"
    __table_args__ = (
        UniqueConstraint("campaign_id", "idempotency_key", name="uq_image_campaign_key"),
        CheckConstraint("request_state IN ('reserved', 'generating', 'ready', 'failed', 'outcome_unknown')", name="ck_image_request_state"),
        CheckConstraint("review_status IN ('draft', 'approved', 'rejected')", name="ck_image_review_status"),
        CheckConstraint("request_state = 'ready' OR review_status = 'draft'", name="ck_image_review_ready"),
        CheckConstraint("request_state != 'ready' OR (storage_key IS NOT NULL AND mime_type IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL AND byte_count IS NOT NULL AND mime_type IN ('image/png', 'image/jpeg') AND width > 0 AND height > 0 AND byte_count > 0 AND checksum IS NOT NULL)", name="ck_image_ready_file"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    source_content_id: Mapped[int] = mapped_column(ForeignKey("generated_contents.id", ondelete="CASCADE"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    source_hash: Mapped[str] = mapped_column(String(64))
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    source_references: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    visual_brief: Mapped[str] = mapped_column(String(2000))
    style: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(100))
    request_state: Mapped[str] = mapped_column(String(30), default="reserved")
    review_status: Mapped[str] = mapped_column(String(20), default="draft")
    storage_key: Mapped[str | None] = mapped_column(String(100))
    mime_type: Mapped[str | None] = mapped_column(String(30))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    byte_count: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64))
    failure_code: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
