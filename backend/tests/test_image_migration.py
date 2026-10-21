from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select

from app.core.config import settings
from app.core.database import Base
from app.models.campaign import Campaign
from app.models.generated_content import GeneratedContent


def test_image_migration_and_downgrade_preserve_existing_text(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'images.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "b7f23e8d10a4")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(Campaign.__table__.insert().values(id=1, title="Existing", objective="Keep", domain="traffic_safety", language="arabic", status="draft", created_at=datetime.now(timezone.utc)))
            connection.execute(GeneratedContent.__table__.insert().values(
                id=1, campaign_id=1, generation_id=uuid4(), language="arabic", content_type="text_package",
                content={"headline": "Existing Arabic text"}, provider="fake", model="test", prompt_version="test",
                input_snapshot={}, source_references=[], review_status="approved", created_at=datetime.now(timezone.utc),
            ))
            before = connection.execute(select(GeneratedContent.__table__)).fetchall()
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert "image_generations" in inspect(connection).get_table_names()
            assert connection.execute(select(GeneratedContent.__table__)).fetchall() == before
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        # Disposable test DB only. The development DB is never downgraded.
        command.downgrade(config, "b7f23e8d10a4")
        with engine.connect() as connection:
            assert "image_generations" not in inspect(connection).get_table_names()
            assert connection.execute(select(GeneratedContent.__table__)).fetchall() == before
    finally:
        engine.dispose()
