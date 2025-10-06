"""Add transcription model

Revision ID: 1324e951528d
Revises: 38fd106d388e
Create Date: 2025-10-06 12:21:24.349207

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1324e951528d"
down_revision: Union[str, Sequence[str], None] = "38fd106d388e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "transcriptions",
        sa.Column(
            "transcription_id",
            sa.String(length=26),
            server_default=sa.text("(ulid())"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("session_id", sa.String(length=26), nullable=False),
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
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("transcription_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("transcriptions")
