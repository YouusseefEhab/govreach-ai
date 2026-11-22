
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.business import Business


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (Index("ix_campaigns_business_created_at_id", "business_id", "created_at", "id"),)

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="traffic_safety",
    )

    objective: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="both",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # A NULL campaign type represents the legacy workflow.
    campaign_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(300), nullable=True)
    business_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    offer_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    channels: Mapped[list[str] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    brief: Mapped[str | None] = mapped_column(Text, nullable=True)

    business_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("businesses.id"), nullable=True,
    )
    business: Mapped[Business | None] = relationship()
