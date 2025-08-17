import pytest

from interview_helper.context_manager.types import ResourceKey
from interview_helper.context_manager.session_context_manager import AppContextManager

pytestmark = pytest.mark.anyio


async def test_context_manager_maintains_individual_state():
    test_resource_key = ResourceKey[str]("string")
    contextManager1 = AppContextManager(())
    contextManager2 = AppContextManager(())

    ctx = await contextManager1.new_session()

    with pytest.raises(AssertionError):
        # Not a valid context for contextManager2
        await contextManager2.register(ctx.session_id, test_resource_key, "hello")

    await ctx.register(test_resource_key, "hello")

    assert await ctx.get(test_resource_key) == "hello"
