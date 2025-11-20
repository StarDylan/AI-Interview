from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.database import add_transcription
from interview_helper.context_manager.messages import TranscriptionMessage
from interview_helper.context_manager.session_context_manager import SessionContext
from interview_helper.context_manager.types import TranscriptId


async def accept_transcript(ctx: SessionContext, text: str, ws: ConcurrentWebSocket):
    # Send transcription data over websocket
    await ws.send_message(TranscriptionMessage(type="transcription", text=text))

    # Add to DB
    added_transcription_id = TranscriptId.from_str(
        add_transcription(
            ctx.manager.db,
            user_id=ctx.get_user_id(),
            session_id=ctx.session_id,
            project_id=ctx.project_id,
            text=text,
        )
    )

    # Ensure the session is aware of it.
    await ctx.accept_transcript(text, added_transcription_id)
