"""initial user table

Revision ID: 38fd106d388e
Revises:
Create Date: 2025-09-19 14:44:19.350301

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "38fd106d388e"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            sa.String(length=26),
            server_default=sa.text("(ulid())"),
            nullable=False,
        ),
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


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("users")
