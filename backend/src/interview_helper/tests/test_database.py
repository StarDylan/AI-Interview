from interview_helper.context_manager.database import init_memory_db_for_test
from sqlalchemy import text
import pytest

pytestmark = pytest.mark.anyio


def test_database_migrations_succeed():
    engine = init_memory_db_for_test()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1")).scalar_one() == 1
