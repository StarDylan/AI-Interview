from interview_helper.context_manager.database import get_user_by_id
from interview_helper.context_manager.database import get_or_add_user_by_oidc_id
from interview_helper.context_manager.database import PersistentDatabase
import sqlalchemy as sa
import pytest

pytestmark = pytest.mark.anyio


def test_database_migrations_succeed():
    engine = PersistentDatabase.new_in_memory().engine
    with engine.connect() as conn:
        conn.execute(sa.text("SELECT 1")).scalar_one() == 1


def test_ulid_extension_loaded():
    engine = PersistentDatabase.new_in_memory().engine
    with engine.connect() as conn:
        ulid = conn.execute(sa.text("SELECT ulid()")).scalar_one()
        assert len(ulid) > 0


def test_user_addition():
    db = PersistentDatabase.new_in_memory()

    test_user_name = "Test User"
    oidc_id = "test-oidc-id"

    added_user = get_or_add_user_by_oidc_id(db, oidc_id, test_user_name)

    added_user3 = get_or_add_user_by_oidc_id(db, oidc_id, "another_name")
    added_user2 = get_user_by_id(db, added_user.user_id)

    assert added_user2 is not None

    # Check that all of them are the same
    assert added_user == added_user2 == added_user3
