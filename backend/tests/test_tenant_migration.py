import sqlite3
from uuid import UUID

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import delete, event, insert, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Business, Campaign, GeneratedContent, Membership, User


PHASE_ONE = "c1a6e9237f4b"


@pytest.fixture
def tenant_migration_db(request):
    if request.config.getoption("--postgres-integration"):
        return request.getfixturevalue("postgres_migration_db")

    def enable_foreign_keys(connection, _):
        # Include Alembic's own connections, so a table rebuild would exercise the real cascade.
        if isinstance(connection, sqlite3.Connection):
            connection.execute("PRAGMA foreign_keys=ON")

    event.listen(Engine, "connect", enable_foreign_keys)
    request.addfinalizer(lambda: event.remove(Engine, "connect", enable_foreign_keys))
    return request.getfixturevalue("migration_db")


def test_tenant_migration_preserves_phase_one_campaigns_and_content(tenant_migration_db):
    config, engine = tenant_migration_db
    campaigns = text("SELECT * FROM campaigns ORDER BY id")
    contents = text("SELECT * FROM generated_contents ORDER BY id")

    command.upgrade(config, PHASE_ONE)
    with engine.begin() as connection:
        connection.execute(insert(Campaign.__table__).values(
            id=10, title="Seat belts", domain="traffic_safety", objective="Buckle up",
        ))
        connection.execute(insert(Campaign.__table__).values(
            id=20, title="Weekend bakery", domain="marketing", objective="Grow pickup orders",
            campaign_type="marketing", business_name="Bakery", target_audience="Local families",
            offer_summary="Pastry box", budget_amount="20.50", budget_currency="USD", channels=["email"],
        ))
        connection.execute(insert(GeneratedContent.__table__), [
            {
                "id": campaign_id + offset, "campaign_id": campaign_id, "generation_id": UUID(int=campaign_id),
                "language": language, "provider": "fake", "model": "fixture", "prompt_version": "fixture-v1",
                "content": {
                    "headline": "A saved headline", "slogan": "Saved slogan", "awareness_message": "Saved message",
                    "social_caption": "Saved caption", "call_to_action": "Saved action",
                },
                "input_snapshot": {"audience": "Saved audience"},
                "source_references": [{"id": "who-seat-belts"}] if campaign_id == 10 else [],
                "review_status": "approved" if campaign_id == 10 else "draft",
            }
            for campaign_id in (10, 20)
            for offset, language in enumerate(("english", "arabic"))
        ])
        original_campaigns = [dict(row) for row in connection.execute(campaigns).mappings()]
        original_contents = connection.execute(contents).all()
        original_content_fks = inspect(connection).get_foreign_keys("generated_contents")

    command.upgrade(config, "head")
    with engine.begin() as connection:
        migration = MigrationContext.configure(connection)
        assert migration.get_current_revision() == ScriptDirectory.from_config(config).get_current_head()
        assert compare_metadata(migration, Base.metadata) == []
        assert list(connection.execute(campaigns).mappings()) == [
            {**row, "business_id": None} for row in original_campaigns
        ]
        assert connection.execute(contents).all() == original_contents
        assert inspect(connection).get_foreign_keys("generated_contents") == original_content_fks

        connection.execute(delete(Campaign).where(Campaign.id == 10))
        assert connection.execute(contents).all() == original_contents[2:]

    command.downgrade(config, PHASE_ONE)
    with engine.connect() as connection:
        assert list(connection.execute(campaigns).mappings()) == original_campaigns[1:]
        assert connection.execute(contents).all() == original_contents[2:]


def test_tenant_schema_enforces_constraints_and_resolves_orm_relationships(tenant_migration_db):
    config, engine = tenant_migration_db
    command.upgrade(config, "head")
    inspector = inspect(engine)
    for table, index, columns in (
        ("campaigns", "ix_campaigns_business_created_at_id", ["business_id", "created_at", "id"]),
        ("memberships", "ix_memberships_user_id_business_id", ["user_id", "business_id"]),
    ):
        assert {index_info["name"]: index_info["column_names"] for index_info in inspector.get_indexes(table)}[
            index
        ] == columns
    assert inspector.get_pk_constraint("memberships")["constrained_columns"] == ["business_id", "user_id"]

    with Session(engine) as session, session.begin():
        user = User(email="Owner@example.test", email_normalized="owner@example.test", password_hash="fixture hash")
        member = User(email="Reader@example.test", email_normalized="reader@example.test", password_hash="fixture hash")
        first = Business(display_name="First shop", default_locale="ar-EG")
        second = Business(display_name="Second shop")
        campaign_business = Business(display_name="Shop with a campaign and no members")
        campaign = Campaign(title="Assigned campaign", objective="Verify relationship", business=campaign_business)
        session.add_all([
            Membership(user=user, business=first, role="owner"),
            Membership(user=user, business=second, role="editor"),
            Membership(user=member, business=first, role="viewer"),
            campaign,
        ])
        session.flush()
        first_id, second_id, user_id, member_id = first.id, second.id, user.id, member.id
        campaign_id, campaign_business_id = campaign.id, campaign_business.id

    with Session(engine) as session, session.begin():
        campaign = session.get(Campaign, campaign_id)
        membership = session.get(Membership, (first_id, user_id))
        assert isinstance(campaign.business_id, UUID)
        assert campaign.business.id == campaign_business_id
        assert membership.business.default_locale == "ar-EG"
        assert membership.user.email == "Owner@example.test"
        assert membership.user.email_verified_at is None and membership.user.disabled_at is None
        assert session.get(Membership, (second_id, user_id)).role == "editor"
        assert session.get(Membership, (first_id, member_id)).role == "viewer"

        missing = UUID(int=1)
        for statement in (
            insert(User).values(email="OWNER@example.test", email_normalized="owner@example.test", password_hash="test"),
            insert(Membership).values(business_id=first_id, user_id=user_id, role="editor"),
            insert(Membership).values(business_id=second_id, user_id=member_id, role="admin"),
            insert(Membership).values(business_id=missing, user_id=user_id, role="viewer"),
            insert(Membership).values(business_id=second_id, user_id=missing, role="editor"),
            insert(Campaign).values(title="Bad owner", objective="Check FK", business_id=missing),
            delete(Business).where(Business.id == campaign_business_id),
            delete(Business).where(Business.id == first_id),
            delete(User).where(User.id == member_id),
        ):
            with pytest.raises(IntegrityError), session.begin_nested():
                session.execute(statement)
