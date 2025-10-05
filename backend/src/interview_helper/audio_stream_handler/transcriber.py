from interview_helper.context_manager.messages import TranscriptionMessage
from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.resource_keys import WEBSOCKET
from interview_helper.context_manager.resource_keys import TRANSCRIBER_SESSION
from vosk import KaldiRecognizer
from vosk import Model
from interview_helper.audio_stream_handler.types import AudioChunk
from interview_helper.context_manager.session_context_manager import SessionContext
import numpy as np
import json


async def vosk_close_transcriber(ctx: SessionContext):
    rec = await ctx.get(TRANSCRIBER_SESSION)
    ws = await ctx.get_or_wait(WEBSOCKET)

    if rec is not None:
        await accept_transcript(ctx, rec.FinalResult(), ws)


async def vosk_transcribe_audio_consumer(ctx: SessionContext, audio_chunk: AudioChunk):
    # Open the wave file once and keep it open across writes
    # so we can batch writes efficiently and finalize
    # the file size at the end.
    rec = await ctx.get(TRANSCRIBER_SESSION)
    ws = await ctx.get_or_wait(WEBSOCKET)

    if rec is None:
        model = Model(str(ctx.get_settings().vosk_model_path.absolute()))
        rec = KaldiRecognizer(model, audio_chunk.framerate)
        rec.SetWords(True)
        rec.SetPartialWords(True)
        await ctx.register(TRANSCRIBER_SESSION, rec)

    for chunk in audio_chunk.data:
        # Ensure dtype and contiguity
        buf = (
            chunk.reshape(-1, audio_chunk.number_of_channels)
            .mean(axis=1)
            .astype(np.int16)
            .tobytes()
        )

        if rec.AcceptWaveform(buf):
            # Finalized segment
            await accept_transcript(ctx, json.loads(rec.Result()), ws)


async def accept_transcript(ctx: SessionContext, data, ws: ConcurrentWebSocket):
    text = data["text"]

    # Send transcription data over websocket
    await ws.send_message(TranscriptionMessage(type="transcription", text=text))


transcriber_consumer_pair = (
    vosk_transcribe_audio_consumer,
    vosk_close_transcriber,
)


def to_mono_pcm16(chunk: AudioChunk) -> AudioChunk:
    """
    Convert the AudioChunk (which may have multiple channels) to mono, 16-bit PCM.
    If it's already mono, this is mostly a no-op (just ensures dtype).
    If multichannel, average.
    """
    # Stack all blocks into one contiguous array along time (1D per block, or 2D per block)
    # First, assume each block is shape (n_samples, n_channels)
    blocks = chunk.data

    # Ensure dtype is int16
    # (If blocks are already int16, this is cheap; else it casts.)
    blocks = [b.astype(np.int16, copy=False) for b in blocks]

    # Convert each block to mono
    mono_blocks = []
    for b in blocks:
        # b is shape (n_samples, n_channels)
        # But careful: mean of ints gives float; so do sum and divide
        # We prefer to avoid overflow, so convert to a wider int (e.g. int32)
        # Then back to int16
        mono = b.astype(np.int32).sum(axis=1) // chunk.number_of_channels
        mono = mono.astype(np.int16)
        mono_blocks.append(mono)

    # Concatenate into one 1D array
    result = np.concatenate(mono_blocks, axis=0)

    chunk = AudioChunk(
        data=[result],
        framerate=chunk.framerate,
        number_of_channels=1,
    )

    return chunk
