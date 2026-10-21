"""Add image request metadata without changing text data or constraints."""

from alembic import op
import sqlalchemy as sa

revision = "c9e51a70d682"
down_revision = "b7f23e8d10a4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "image_generations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_content_id", sa.Integer(), sa.ForeignKey("generated_contents.id", ondelete="CASCADE"), nullable=False),
        *[sa.Column(name, sa.String(length), nullable=False) for name, length in [
            ("idempotency_key", 128), ("request_hash", 64), ("source_hash", 64),
            ("visual_brief", 2000), ("style", 40), ("provider", 100), ("model", 100),
            ("prompt_version", 100), ("request_state", 30), ("review_status", 20),
        ]],
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        *[sa.Column(name, sa.String(length), nullable=True) for name, length in [
            ("storage_key", 100), ("mime_type", 30), ("checksum", 64), ("failure_code", 50),
        ]],
        *[sa.Column(name, sa.Integer(), nullable=True) for name in ("width", "height", "byte_count")],
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("campaign_id", "idempotency_key", name="uq_image_campaign_key"),
        sa.CheckConstraint("request_state IN ('reserved', 'generating', 'ready', 'failed', 'outcome_unknown')", name="ck_image_request_state"),
        sa.CheckConstraint("review_status IN ('draft', 'approved', 'rejected')", name="ck_image_review_status"),
        sa.CheckConstraint("request_state = 'ready' OR review_status = 'draft'", name="ck_image_review_ready"),
        sa.CheckConstraint("request_state != 'ready' OR (storage_key IS NOT NULL AND mime_type IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL AND byte_count IS NOT NULL AND mime_type IN ('image/png', 'image/jpeg') AND width > 0 AND height > 0 AND byte_count > 0 AND checksum IS NOT NULL)", name="ck_image_ready_file"),
    )
    op.create_index("ix_image_generations_campaign_id", "image_generations", ["campaign_id"])
    op.create_index("ix_image_generations_source_content_id", "image_generations", ["source_content_id"])


def downgrade():
    # Explicit downgrade removes image metadata, not files or existing text rows.
    op.drop_index("ix_image_generations_source_content_id", table_name="image_generations")
    op.drop_index("ix_image_generations_campaign_id", table_name="image_generations")
    op.drop_table("image_generations")
