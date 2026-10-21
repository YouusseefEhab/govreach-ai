from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings
from app.core.database import Base


def test_migration_preserves_existing_campaign_and_matches_models(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "851ce324628e")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO campaigns (id, title, domain, objective, language, status, created_at) "
                "VALUES (1, 'Existing campaign', 'traffic_safety', 'Keep this', 'both', 'draft', '2026-10-13')"
            ))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT title FROM campaigns WHERE id=1")).scalar() == "Existing campaign"
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "c9e51a70d682"
            foreign_key = inspect(connection).get_foreign_keys("generated_contents")[0]
            assert foreign_key["referred_table"] == "campaigns"
            assert foreign_key["options"]["ondelete"] == "CASCADE"
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        # Downgrade only on this disposable test DB, never the user's PostgreSQL.
        command.downgrade(config, "851ce324628e")
        with engine.connect() as connection:
            assert "generated_contents" not in inspect(connection).get_table_names()
            assert connection.execute(text("SELECT title FROM campaigns WHERE id=1")).scalar() == "Existing campaign"
    finally:
        engine.dispose()
