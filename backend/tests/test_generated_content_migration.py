import json
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text

from app.core.config import settings
from app.core.database import Base


INSERT_LEGACY_CAMPAIGN = text(
    "INSERT INTO campaigns (id, title, domain, objective, language, status, created_at) "
    "VALUES (:id, 'Existing campaign', 'traffic_safety', 'Keep this', 'both', 'draft', '2026-10-13')"
)


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        yield config, engine
    finally:
        engine.dispose()


def test_generated_content_migration_preserves_existing_campaign(migration_db):
    config, engine = migration_db
    command.upgrade(config, "851ce324628e")
    with engine.begin() as connection:
        connection.execute(INSERT_LEGACY_CAMPAIGN, {"id": 1})

    command.upgrade(config, "b7f23e8d10a4")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM campaigns WHERE id=1")).scalar() == "Existing campaign"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "b7f23e8d10a4"
        foreign_key = inspect(connection).get_foreign_keys("generated_contents")[0]
        assert foreign_key["referred_table"] == "campaigns"
        assert foreign_key["options"]["ondelete"] == "CASCADE"

    command.downgrade(config, "851ce324628e")
    with engine.connect() as connection:
        assert "generated_contents" not in inspect(connection).get_table_names()
        assert connection.execute(text("SELECT title FROM campaigns WHERE id=1")).scalar() == "Existing campaign"


def test_marketing_migration_preserves_legacy_data_and_cascade(migration_db):
    config, engine = migration_db
    legacy_campaigns = text(
        "SELECT id, title, domain, objective, language, status, created_at FROM campaigns ORDER BY id"
    )
    generated_contents = text("SELECT * FROM generated_contents ORDER BY id")
    marketing_fields = text(
        "SELECT campaign_type, target_audience, business_name, offer_summary, budget_amount, "
        "budget_currency, channels, brief FROM campaigns ORDER BY id"
    )

    command.upgrade(config, "b7f23e8d10a4")
    with engine.begin() as connection:
        connection.execute(INSERT_LEGACY_CAMPAIGN, [{"id": 1}, {"id": 2}])
        connection.execute(
            text(
                "INSERT INTO generated_contents "
                "(id, campaign_id, generation_id, language, content_type, content, provider, model, "
                "prompt_version, input_snapshot, source_references, review_status, created_at) "
                "VALUES (:id, :id, :generation_id, 'english', 'text_package', :content, 'fake', "
                "'test-model', 'traffic-text-v2-sourced', :snapshot, :sources, 'approved', '2026-10-13')"
            ),
            [
                {
                    "id": campaign_id,
                    "generation_id": f"{campaign_id:032x}",
                    "content": json.dumps({
                        "headline": "Buckle up",
                        "slogan": "Click every trip",
                        "awareness_message": "Wear your seat belt",
                        "social_caption": "Buckle up before setting off",
                        "call_to_action": "Fasten your seat belt",
                    }),
                    "snapshot": json.dumps({"domain": "traffic_safety", "audience": "Drivers"}),
                    "sources": json.dumps([{"id": "who-seat-belts"}]),
                }
                for campaign_id in (1, 2)
            ],
        )
        previous_campaigns = connection.execute(legacy_campaigns).all()
        previous_contents = connection.execute(generated_contents).all()

    command.upgrade(config, "head")
    with engine.begin() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == (
            ScriptDirectory.from_config(config).get_current_head()
        )
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        assert connection.execute(legacy_campaigns).all() == previous_campaigns
        assert connection.execute(generated_contents).all() == previous_contents
        assert connection.execute(marketing_fields).all() == [(None,) * 8] * 2

        connection.execute(INSERT_LEGACY_CAMPAIGN, {"id": 3})
        assert connection.execute(marketing_fields).all() == [(None,) * 8] * 3

        connection.execute(text("DELETE FROM campaigns WHERE id=1"))
        assert connection.execute(generated_contents).all() == previous_contents[1:]
        remaining_campaigns = connection.execute(legacy_campaigns).all()

    command.downgrade(config, "b7f23e8d10a4")
    with engine.connect() as connection:
        assert [column["name"] for column in inspect(connection).get_columns("campaigns")] == (
            list(connection.execute(legacy_campaigns).keys())
        )
        assert connection.execute(legacy_campaigns).all() == remaining_campaigns
        assert connection.execute(generated_contents).all() == previous_contents[1:]
