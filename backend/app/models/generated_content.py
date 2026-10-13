from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GeneratedContent(Base):
    __tablename__ = "generated_contents"
    __table_args__ = (
        UniqueConstraint("generation_id", "language", name="uq_generated_contents_generation_language"),
        CheckConstraint("language IN ('arabic', 'english')", name="ck_generated_contents_language"),
        CheckConstraint("content_type = 'text_package'", name="ck_generated_contents_content_type"),
        CheckConstraint("review_status IN ('draft', 'approved', 'rejected')", name="ck_generated_contents_review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    generation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text_package")
    content: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_references: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
