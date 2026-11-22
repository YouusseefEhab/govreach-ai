"""Add nullable campaign metadata for marketing.

Revision ID: c1a6e9237f4b
Revises: b7f23e8d10a4
"""

from alembic import op
import sqlalchemy as sa


revision = "c1a6e9237f4b"
down_revision = "b7f23e8d10a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("campaign_type", sa.String(20), nullable=True))
    op.add_column("campaigns", sa.Column("target_audience", sa.String(300), nullable=True))
    op.add_column("campaigns", sa.Column("business_name", sa.String(120), nullable=True))
    op.add_column("campaigns", sa.Column("offer_summary", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("budget_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("campaigns", sa.Column("budget_currency", sa.String(3), nullable=True))
    op.add_column("campaigns", sa.Column("channels", sa.JSON(none_as_null=True), nullable=True))
    op.add_column("campaigns", sa.Column("brief", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "brief")
    op.drop_column("campaigns", "channels")
    op.drop_column("campaigns", "budget_currency")
    op.drop_column("campaigns", "budget_amount")
    op.drop_column("campaigns", "offer_summary")
    op.drop_column("campaigns", "business_name")
    op.drop_column("campaigns", "target_audience")
    op.drop_column("campaigns", "campaign_type")
