"""Create generated content storage without altering existing campaigns.

Revision ID: b7f23e8d10a4
Revises: 851ce324628e
"""

from alembic import op
import sqlalchemy as sa


revision = "b7f23e8d10a4"
down_revision = "851ce324628e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("generation_id", "language", name="uq_generated_contents_generation_language"),
        sa.CheckConstraint("language IN ('arabic', 'english')", name="ck_generated_contents_language"),
        sa.CheckConstraint("content_type = 'text_package'", name="ck_generated_contents_content_type"),
        sa.CheckConstraint("review_status IN ('draft', 'approved', 'rejected')", name="ck_generated_contents_review_status"),
    )
    op.create_index("ix_generated_contents_campaign_id", "generated_contents", ["campaign_id"])


def downgrade() -> None:
    # Explicitly running this downgrade removes generated content and its history.
    op.drop_index("ix_generated_contents_campaign_id", table_name="generated_contents")
    op.drop_table("generated_contents")
