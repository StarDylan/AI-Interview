from collections.abc import Sequence
from sqlalchemy.sql.sqltypes import DateTime
from typing import TypedDict
from interview_helper.context_manager.types import ProjectId, SessionId
from interview_helper.context_manager.types import UserId
from alembic.config import Config
from alembic import command
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy.event import listen as sa_listen
from contextlib import contextmanager
from dataclasses import dataclass
import interview_helper.context_manager.models as models
import sqlite_ulid


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
            sa.select(
                models.User.user_id, models.User.full_name, models.User.oidc_id
            ).where(models.User.user_id == str(user_id))
        ).one_or_none()

        if result is not None:
            user_id_str, full_name, oidc_id = result.tuple()
            return UserResult(
                user_id=UserId.from_str(user_id_str),
                full_name=full_name,
                oidc_id=oidc_id,
            )

        return None


def get_or_add_user_by_oidc_id(
    db: PersistentDatabase, oidc_id: str, full_name: str
) -> UserResult:
    """
    Get or add a user by oidc_id. Uses the existing name if found.
    """
    with db.begin() as conn:
        result = conn.execute(
            sa.select(models.User.user_id, models.User.full_name).where(
                models.User.oidc_id == oidc_id
            )
        ).one_or_none()

        if result is not None:
            user_id, full_name = result.tuple()
            return UserResult(
                user_id=UserId.from_str(user_id),
                full_name=full_name,
                oidc_id=oidc_id,
            )

        (user_id,) = (
            conn.execute(
                sa.insert(models.User).returning(models.User.user_id),
                {"full_name": full_name, "oidc_id": oidc_id},
            )
            .one()
            .tuple()
        )

        return UserResult(
            user_id=UserId.from_str(user_id),
            full_name=full_name,
            oidc_id=oidc_id,
        )


def add_transcription(
    db: PersistentDatabase,
    user_id: UserId,
    session_id: SessionId,
    project_id: ProjectId,
    text: str,
) -> str:
    """
    Adds a transcription result, returns the transcription ID
    """
    with db.begin() as conn:
        result = conn.scalar(
            sa.insert(models.Transcription).returning(
                models.Transcription.transcription_id
            ),
            {
                "user_id": str(user_id),
                "session_id": str(session_id),
                "project_id": str(project_id),
                "text_output": text,
            },
        )

    assert result, (
        f"Transcription not created in DB! session_id: {session_id}, text:'{text}'"
    )
    return result


def get_all_transcripts(db: PersistentDatabase, project_id: ProjectId) -> list[str]:
    """
    Gets all transcript results, sorted by creation date (ascending)
    """
    with db.begin() as conn:
        rows = (
            conn.execute(
                sa.select(models.Transcription.text_output)
                .where(models.Transcription.project_id == str(project_id))
                .order_by(models.Transcription.created_at.asc())
            )
            .scalars()
            .all()
        )

    return list(rows)


class ProjectListing(TypedDict):
    id: str
    name: str
    creator_name: str
    created_at: str


def get_all_projects(db: PersistentDatabase) -> Sequence[ProjectListing]:
    """
    Gets all projects with creator name and creation date, sorted by creation date (descending)
    """
    with db.begin() as conn:
        rows: Sequence[tuple[str, str, str, DateTime]] = (
            conn.execute(
                sa.select(
                    models.Project.project_id,
                    models.Project.name,
                    models.User.full_name,
                    models.Project.created_at,
                )
                .join(
                    models.User, models.Project.creator_user_id == models.User.user_id
                )
                .order_by(models.Project.created_at.desc())
            )
            .tuples()
            .all()
        )

    projects: list[ProjectListing] = []
    for project_id, project_name, creator_name, created_at in rows:
        projects.append(
            {
                "id": project_id,
                "name": project_name,
                "creator_name": creator_name,
                "created_at": created_at.isoformat(),  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
            }
        )

    return projects


def create_new_project(
    db: PersistentDatabase, user_id: UserId, project_name: str
) -> ProjectListing:
    """
    Creates a new project and returns the project ID
    """
    user = get_user_by_id(db, user_id)
    assert user, (
        f"User that doesn't exist (ID: {user_id}) is trying to create project: {project_name}"
    )

    with db.begin() as conn:
        result = conn.execute(
            sa.insert(models.Project).returning(
                models.Project.project_id, models.Project.created_at
            ),
            {
                "creator_user_id": str(user.user_id),
                "name": project_name,
            },
        )

        project_id, created_at = result.one().tuple()

    return {
        "id": project_id,
        "name": project_name,
        "creator_name": user.full_name,
        "created_at": created_at.isoformat(),  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
    }


def get_project_by_id(
    db: PersistentDatabase, project_id: ProjectId
) -> ProjectListing | None:
    """
    Gets a single project by ID with creator information
    """
    with db.begin() as conn:
        result = conn.execute(
            sa.select(
                models.Project.project_id,
                models.Project.name,
                models.User.full_name,
                models.Project.created_at,
            )
            .join(models.User, models.Project.creator_user_id == models.User.user_id)
            .where(models.Project.project_id == str(project_id))
        ).one_or_none()

        if result is None:
            return None

        project_id_str, project_name, creator_name, created_at = result.tuple()

        return {
            "id": project_id_str,
            "name": project_name,
            "creator_name": creator_name,
            "created_at": created_at.isoformat(),  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
        }


def get_all_ai_analyses(db: PersistentDatabase, project_id: ProjectId) -> list[str]:
    """
    Gets all AI analysis results for a project, sorted by creation date (ascending)
    Note: Currently AIAnalysis table doesn't have project_id or created_at fields.
    This is a placeholder implementation that returns all analyses.
    """
    with db.begin() as conn:
        rows = (
            conn.execute(
                sa.select(models.AIAnalysis.text)
                .order_by(models.AIAnalysis.analysis_id.asc())
                .where(models.AIAnalysis.project_id == str(project_id))
            )
            .scalars()
            .all()
        )

    return list(rows)


def add_ai_analysis(
    db: PersistentDatabase,
    project_id: ProjectId,
    text: str,
):
    """
    Adds a transcription result, returns the transcription ID
    """
    with db.begin() as conn:
        _ = conn.execute(
            sa.insert(models.AIAnalysis),
            {
                "project_id": str(project_id),
                "text": text,
            },
        )
