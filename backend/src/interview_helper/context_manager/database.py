from sqlalchemy import create_engine
from alembic.config import Config
from alembic import command
from pathlib import Path


def init_db():
    return create_engine("sqlite+pysqlite:///database.sqlite3")


def init_memory_db_for_test():
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)

    alembic_dir = Path(__file__).parent.parent.parent.parent / "alembic"

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(alembic_dir))

    # Dark magic to get the in-memory database to alembic.
    alembic_cfg.attributes["connectable"] = engine

    command.upgrade(alembic_cfg, "head")

    return engine
