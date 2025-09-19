from interview_helper.context_manager.types import UserId
from alembic.config import Config
from alembic import command
from pathlib import Path
import sqlite_ulid
import sqlalchemy as sa
from sqlalchemy.event import listen as sa_listen
from contextlib import contextmanager
from dataclasses import dataclass


class PersistentDatabase:
    """A persistent database that is saved to local disk"""

    DATABASE_URL = "sqlite+pysqlite:///database.sqlite3"

    def __init__(self, engine: sa.Engine | None = None):
        if engine is None:
            engine = sa.create_engine(PersistentDatabase.DATABASE_URL)

        self.engine = engine
        self._setup_extensions()

    @classmethod
    def new_in_memory(cls):
        """
        A constructor for creating a persistent database in memory for testing
        """
        new_persistent_db = cls(
            engine=sa.create_engine("sqlite+pysqlite:///:memory:", echo=True)
        )

        new_persistent_db._run_migrations_for_testing()

        return new_persistent_db

    @contextmanager
    def begin(self):
        with self.engine.begin() as conn:
            yield conn

    def _run_migrations_for_testing(self):
        """
        We expect for production that the user runs the migration themselves, but for
        unit tests we must invoke it ourselves.
        """
        alembic_dir = Path(__file__).parent.parent.parent.parent / "alembic"

        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(alembic_dir))

        # Dark magic to get the in-memory database to alembic.
        alembic_cfg.attributes["connectable"] = self.engine

        command.upgrade(alembic_cfg, "head")

    def _setup_extensions(self):
        def load_extension(conn, unused):
            conn.enable_load_extension(True)
            sqlite_ulid.load(conn)
            conn.enable_load_extension(False)

        sa_listen(self.engine, "connect", load_extension)


@dataclass
class UserResult:
    user_id: UserId
    full_name: str
    oidc_id: str


def get_user_by_id(db: PersistentDatabase, user_id: UserId) -> UserResult | None:
    """
    Returns the user given their user_id
    """
    with db.begin() as conn:
        result = conn.execute(
            sa.text(
                "SELECT user_id, full_name, oidc_id FROM users WHERE user_id = :user_id"
            ),
            {"user_id": str(user_id)},
        ).one_or_none()

        if result is not None:
            print(result.user_id)
            return UserResult(
                user_id=UserId.from_str(result.user_id),
                full_name=result.full_name,
                oidc_id=result.oidc_id,
            )

        return None


def get_or_add_user(db: PersistentDatabase, oidc_id: str, full_name: str) -> UserResult:
    """
    Get or add a user by oidc_id. Uses the existing name if found.
    """
    with db.begin() as conn:
        result = conn.execute(
            sa.text("SELECT user_id, full_name FROM users WHERE oidc_id = :oidc_id"),
            {"oidc_id": oidc_id},
        ).one_or_none()

        if result is not None:
            return UserResult(
                user_id=UserId.from_str(result.user_id),
                full_name=result.full_name,
                oidc_id=oidc_id,
            )

        conn.execute(
            sa.text(
                "INSERT INTO users (full_name, oidc_id) VALUES (:full_name, :oidc_id)"
            ),
            {"full_name": full_name, "oidc_id": oidc_id},
        )

        result = conn.execute(
            sa.text("SELECT user_id FROM users WHERE oidc_id = :oidc_id"),
            {"oidc_id": oidc_id},
        ).one()

        return UserResult(
            user_id=UserId.from_str(result.user_id),
            full_name=full_name,
            oidc_id=oidc_id,
        )
