import azure.cognitiveservices.speech as speechsdk  # pyright: ignore[reportMissingTypeStubs]

from interview_helper.audio_stream_handler.transcription.common import accept_transcript
from interview_helper.audio_stream_handler.types import AudioChunk
from interview_helper.context_manager.resource_keys import (
    AZURE_AUDIO_FORMAT,
    AZURE_STREAM,
    AZURE_TRANSCRIBER,
    WEBSOCKET,
)
from interview_helper.context_manager.session_context_manager import SessionContext

import os
from anyio import from_thread, to_thread
import numpy as np
import logging

logger = logging.getLogger(__name__)

# pyright: reportUnknownVariableType=none


async def setup_and_get_azure_transcriber(
    ctx: SessionContext, first_chunk_rate_hz: int
):
    transcriber = await ctx.get(AZURE_TRANSCRIBER)
    if transcriber is not None:
        return transcriber

    # --- Speech config ---
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not speech_region:
        raise RuntimeError("Missing AZURE_SPEECH_KEY / AZURE_SPEECH_REGION env vars")

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key, region=speech_region
    )
    speech_config.speech_recognition_language = "en-US"

    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults, "true"
    )

    # --- Audio format + stream ---
    # Use the input sample rate of your chunks; Azure handles common rates (16k/24k/44.1k/48k).
    fmt = speechsdk.audio.AudioStreamFormat(
        samples_per_second=int(first_chunk_rate_hz), bits_per_sample=16, channels=1
    )
    stream = speechsdk.audio.PushAudioInputStream(fmt)
    audio_input = speechsdk.AudioConfig(stream=stream)

    # --- Transcriber (does diarization) ---
    transcriber = speechsdk.transcription.ConversationTranscriber(
        speech_config=speech_config, audio_config=audio_input
    )

    # ---- Event handlers ----
    ws = await ctx.get_or_wait(WEBSOCKET)

    def _publish_transcript_part(text: str, speaker_id: str | None):
        # Prepend speaker tag so your downstream sees who said what.
        spk = speaker_id or "Unknown"
        line = f"[{spk}] {text}".strip()

        from_thread.run(accept_transcript, ctx, line, ws)

    def on_transcribed(evt: speechsdk.transcription.ConversationTranscriptionEventArgs):
        if (
            evt.result.reason == speechsdk.ResultReason.RecognizedSpeech
            and evt.result.text
        ):
            _publish_transcript_part(
                evt.result.text, getattr(evt.result, "speaker_id", None)
            )

    transcriber.transcribed.connect(on_transcribed)  # pyright: ignore[reportUnknownMemberType]

    # Start the pipeline + wait for start in seperate thread to not block event loop
    _ = await to_thread.run_sync(transcriber.start_transcribing_async().get)

    # Stash for reuse
    await ctx.register(AZURE_TRANSCRIBER, transcriber)
    await ctx.register(AZURE_STREAM, stream)
    await ctx.register(AZURE_AUDIO_FORMAT, fmt)
    return transcriber


async def azure_transcribe_audio_consumer(ctx: SessionContext, audio_chunk: AudioChunk):
    """
    Same signature & behavior as your Vosk consumer:
    - Consumes AudioChunk(data: list[np.ndarray[int16 or float]], framerate: int, number_of_channels: int)
    - Pushes bytes to Azure
    - Emits finalized lines via accept_transcript(ctx, text, ws)
    """
    # Create (or reuse) the Azure transcriber + stream
    _ = await setup_and_get_azure_transcriber(
        ctx, first_chunk_rate_hz=audio_chunk.framerate
    )
    stream = await ctx.get(AZURE_STREAM)
    assert stream, f"stream in {ctx.session_id} is not initialized!"

    # For each ndarray in .data, convert to mono int16 little-endian and push
    for chunk in audio_chunk.data:
        # Ensure contiguous mono int16
        buf = (  # pyright: ignore[reportAny]
            chunk.reshape(-1, audio_chunk.number_of_channels)  # pyright: ignore[reportAny]
            .mean(axis=1)
            .astype(np.int16)
            .tobytes()
        )
        stream.write(buf)  # pyright: ignore[reportAny]


async def azure_transcribe_stop(ctx: SessionContext):
    """
    Call this when you're done with the stream (e.g., end of call/meeting).
    """
    transcriber = await ctx.get(AZURE_TRANSCRIBER)
    stream = await ctx.get(AZURE_STREAM)

    if stream:
        stream.close()

    if transcriber:
        _ = await to_thread.run_sync(transcriber.stop_transcribing_async().get)
