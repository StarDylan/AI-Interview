from sqlalchemy.orm._orm_constructors import relationship
from sqlalchemy.sql.schema import ForeignKey
import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from sqlalchemy import DateTime, text


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(
        sa.String(26), primary_key=True, server_default=text("ulid()")
    )
    full_name: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)
    oidc_id: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True)
    updated_at: Mapped[DateTime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id!r}, full_name={self.full_name!r})"


class Transcription(Base):
    __tablename__ = "transcriptions"

    transcription_id: Mapped[str] = mapped_column(
        sa.String(26), primary_key=True, server_default=text("ulid()")
    )
    user_id: Mapped[str] = mapped_column(
        sa.String(26), ForeignKey("users.user_id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(sa.String(26), nullable=False)

    text_output: Mapped[str] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="transcriptions")
