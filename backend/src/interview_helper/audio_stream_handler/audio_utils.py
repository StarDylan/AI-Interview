from interview_helper.context_manager.resource_keys import WAVE_WRITE_FD
from wave import Wave_write
from interview_helper.audio_stream_handler.types import PCMAudioArray
from pathlib import Path
import numpy as np
from av.audio.frame import AudioFrame
import wave
import logging
import anyio.to_thread

from interview_helper.context_manager.session_context_manager import SessionContext

from interview_helper.audio_stream_handler.types import AudioChunk

logger = logging.getLogger(__name__)


def to_pcm(
    frame: AudioFrame,
) -> AudioChunk:
    chunks: list[PCMAudioArray] = []

    # Causes a robotic voice.
    # resampler = AudioResampler(
    #     format="s16p",
    #     layout=layout,
    #     rate=target_rate,
    # )

    # for rframe in resampler.resample(frame):
    rframe = frame
    arr = rframe.to_ndarray()
    pcm = np.asarray(arr, dtype=np.int16)

    chunks.append(pcm)

    return AudioChunk(data=chunks, framerate=frame.sample_rate, number_of_channels=2)


async def close_write_to_disk_audio_consumer(ctx: SessionContext):
    open_wave_fd = await ctx.get(WAVE_WRITE_FD)
    if open_wave_fd is not None:
        open_wave_fd.close()


async def write_to_disk_audio_consumer(ctx: SessionContext, audio_chunk: AudioChunk):
    # Open the wave file once and keep it open across writes
    # so we can batch writes efficiently and finalize
    # the file size at the end.
    open_wave_fd = await ctx.get(WAVE_WRITE_FD)
    if open_wave_fd is None:
        session_dir = (
            Path(ctx.get_settings().audio_recordings_dir)
            / f"recording-{ctx.session_id}.wav"
        )

        open_wave_fd = wave.open(str(session_dir.absolute()), "wb").__enter__()
        open_wave_fd.setnchannels(audio_chunk.number_of_channels)
        open_wave_fd.setsampwidth(2)  # 2 bytes for 16-bit audio
        open_wave_fd.setframerate(audio_chunk.framerate)

        await ctx.register(WAVE_WRITE_FD, open_wave_fd)

    await anyio.to_thread.run_sync(write_pcmaudio_to_wav, audio_chunk, open_wave_fd)


async_audio_write_to_disk_consumer_pair = (
    write_to_disk_audio_consumer,
    close_write_to_disk_audio_consumer,
)


def write_pcmaudio_to_wav(audio_chunk: AudioChunk, open_wave_fd: Wave_write):
    """
    Writes an AudioChunk to a WAV file.
    """

    full_frame = np.concatenate(audio_chunk.data, axis=0)

    open_wave_fd.writeframes(full_frame.tobytes())
