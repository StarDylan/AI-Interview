from interview_helper.context_manager.session_context_manager import AIJob


async def fake_ai_analyzer(job: AIJob) -> None:
    print(f"WARNING: using fake analyzer\nText: {job.new_text} on {job.ctx.session_id}")
