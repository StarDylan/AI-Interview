"""initial

Revision ID: 869cfd49ebd5
Revises:
Create Date: 2025-11-16 14:05:56.431341

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "869cfd49ebd5"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("oidc_id", sa.String(length=255), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("full_name"),
        sa.UniqueConstraint("oidc_id"),
    )
    _ = op.create_table(
        "project",
        sa.Column("project_id", sa.String(length=26), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("creator_user_id", sa.String(length=26), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["creator_user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("project_id"),
    )
    _ = op.create_table(
        "ai_analyses",
        sa.Column("analysis_id", sa.String(length=26), nullable=False),
        sa.Column("project_id", sa.String(length=26), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("span", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
        ),
        sa.PrimaryKeyConstraint("analysis_id"),
    )
    _ = op.create_table(
        "transcriptions",
        sa.Column("transcription_id", sa.String(length=26), nullable=False),
        sa.Column("project_id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("text_output", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("transcription_id"),
    )
    _ = op.create_table(
        "dismissed_ai_analyses",
        sa.Column("dismissed_analysis_id", sa.String(length=26), nullable=False),
        sa.Column("analysis_id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["ai_analyses.analysis_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("dismissed_analysis_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("dismissed_ai_analyses")
    op.drop_table("transcriptions")
    op.drop_table("ai_analyses")
    op.drop_table("project")
    op.drop_table("users")
