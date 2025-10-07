from interview_helper.context_manager.types import AIResult
from interview_helper.context_manager.session_context_manager import AIJob


async def fake_ai_analyzer(job: AIJob) -> list[AIResult]:
    # TODO: Do some AI processing here
    print(
        f"Processing text: {job.session_id} up to transcript {job.up_to_transcript_id}"
    )

    return [
        AIResult(job.session_id, text=f"Up to {job.up_to_transcript_id}"),
        AIResult(job.session_id, text="I am processing btw :)"),
    ]
