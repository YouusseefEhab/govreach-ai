"""Add users, businesses and memberships with nullable campaign ownership."""

import sqlalchemy as sa
from alembic import op


revision = "e4d8cf106a72"
down_revision = "c1a6e9237f4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("email_normalized", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email_normalized", name="uq_users_email_normalized"),
    )
    op.create_table(
        "businesses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("default_locale", sa.String(35), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "memberships",
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'editor', 'viewer')", name="ck_memberships_role"),
    )
    op.create_index("ix_memberships_user_id_business_id", "memberships", ["user_id", "business_id"])

    # Adding the reference inline avoids recreating campaigns and risking a child-row cascade on SQLite.
    # The default immediate NO ACTION foreign key blocks deletion of a referenced business.
    op.add_column(
        "campaigns",
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id"), nullable=True),
        inline_references=True,
    )
    op.create_index("ix_campaigns_business_created_at_id", "campaigns", ["business_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_campaigns_business_created_at_id", table_name="campaigns")
    op.drop_column("campaigns", "business_id")
    op.drop_index("ix_memberships_user_id_business_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("businesses")
    op.drop_table("users")
