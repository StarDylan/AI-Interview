from interview_helper.context_manager.resource_keys import TRANSCRIBER_SESSION
from vosk import KaldiRecognizer
from vosk import Model
from interview_helper.audio_stream_handler.types import AudioChunk
from interview_helper.context_manager.session_context_manager import SessionContext


async def close_transcriber(ctx: SessionContext):
    rec = await ctx.get(TRANSCRIBER_SESSION)

    if rec is not None:
        accept_transcript(ctx, rec.FinalResult())


async def transcribe_audio_consumer(ctx: SessionContext, audio_chunk: AudioChunk):
    # Open the wave file once and keep it open across writes
    # so we can batch writes efficiently and finalize
    # the file size at the end.
    rec = await ctx.get(TRANSCRIBER_SESSION)

    if rec is None:
        model = Model(ctx.get_settings().vosk_model_path)
        rec = KaldiRecognizer(model, audio_chunk.framerate)
        rec.SetWords(True)
        rec.SetPartialWords(True)
        await ctx.register(TRANSCRIBER_SESSION, rec)

    for chunk in audio_chunk.data:
        # Ensure dtype and contiguity
        buf = chunk.tobytes()

        if rec.AcceptWaveform(buf):
            # Finalized segment
            accept_transcript(ctx, rec.Result())


def accept_transcript(ctx: SessionContext, data):
    print(data)


transcriber_consumer_pair = (
    transcribe_audio_consumer,
    close_transcriber,
)
