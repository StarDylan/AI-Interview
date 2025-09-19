from interview_helper.context_manager.database import PersistentDatabase
import sqlalchemy as sa
import pytest

pytestmark = pytest.mark.anyio


def test_database_migrations_succeed():
    engine = PersistentDatabase.new_in_memory().engine
    with engine.connect() as conn:
        conn.execute(sa.text("SELECT 1")).scalar_one() == 1


def test_ulid_extension_loaded():
    engine = PersistentDatabase().new_in_memory().engine
    with engine.connect() as conn:
        ulid = conn.execute(sa.text("SELECT ulid()")).scalar_one()
        assert len(ulid) > 0


def test_user_addition():
    db = PersistentDatabase().new_in_memory()

    test_user_name = "test"

    with db.begin() as conn:
        result = conn.execute(
            sa.text("""
            INSERT INTO "users" (username, oidc_id)
                VALUES (:username, :oidc_id)
                RETURNING user_id
            """),
            {"username": test_user_name, "oidc_id": "test-oidc-id"},
        ).fetchone()

        assert result

        new_user_id = result.user_id
        assert new_user_id is not None

    with db.begin() as conn:
        result = conn.execute(sa.text("""SELECT "user_id" FROM users""")).fetchone()

        assert result

        # Verify that it was successfully added
        assert result.user_id == new_user_id
