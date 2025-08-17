from pathlib import Path
import numpy as np
from numpy.typing import NDArray
from av.audio.frame import AudioFrame
from av.audio.resampler import AudioResampler
import wave
import os
import logging
import anyio.to_thread

from interview_helper.context_manager.session_context_manager import SessionContext

from interview_helper.audio_stream_handler.types import AudioChunk

logger = logging.getLogger(__name__)


def to_pcm(
    frame: AudioFrame,
    *,
    target_rate: int = 44_100,
) -> AudioChunk:
    """
    Convert an av.AudioFrame or av.Packet to PCM NumPy array.

    Args:
        obj: Either an av.AudioFrame (decoded) or av.Packet (encoded audio).
        target_rate: Desired sample rate (None = keep original).
        target_layout: Channel layout ("mono", "stereo", etc.).
        target_format: PCM format ("flt"=float32, "s16"=int16, etc.).

    Returns:
        np.ndarray with shape (samples, channels), PCM audio.
    """
    chunks: list[NDArray] = []

    resampler = AudioResampler(
        format="flt",  # float32 PCM,
        layout="mono",
        rate=target_rate,
    )

    for rframe in resampler.resample(frame):
        array = rframe.to_ndarray()
        newArray = array.astype(np.float32, copy=False)

        pcm = np.moveaxis(newArray, 0, 1)  # (samples, channels)
        chunks.append(pcm)

    data = np.concatenate(chunks, axis=0)

    return AudioChunk(data=data, framerate=target_rate, number_of_channels=1)


async def write_to_disk_audio_consumer(ctx: SessionContext, audio_chunk: AudioChunk):
    path = (
        Path(ctx.get_settings().audio_recordings_dir)
        / f"recording-{ctx.session_id}.wav"
    )
    await anyio.to_thread.run_sync(append_pcmaudio_to_wav, path, audio_chunk)


def write_pcmaudio_to_wav(filepath: Path, audio_chunk: AudioChunk):
    """
    Writes an AudioChunk to a WAV file.

    Args:
        filepath: The path to the output WAV file.
        audio_chunk: The AudioChunk to write. Expected range is -1.0 to 1.0.
    """

    # Scale to 16-bit integer range (-32768 to 32767)
    audio_data_int16 = (audio_chunk.data * (2**15 - 1)).astype(np.int16)

    with wave.open(str(filepath.absolute()), "wb") as wav_file:
        wav_file.setnchannels(audio_chunk.number_of_channels)
        wav_file.setsampwidth(2)  # 2 bytes for 16-bit audio
        wav_file.setframerate(audio_chunk.framerate)
        wav_file.writeframes(audio_data_int16.tobytes())


def append_pcmaudio_to_wav(filepath: Path, audio_chunk: AudioChunk):
    """
    Appends an AudioChunk to an existing WAV file. If the file doesn't exist, it creates a new one.

    Args:
        filename: The path to the WAV file.
        audio_chunk: The AudioChunk to append. Expected range is -1.0 to 1.0.
    """
    if not os.path.exists(filepath):
        # If the file doesn't exist, create it with the initial audio data
        write_pcmaudio_to_wav(filepath, audio_chunk)
        return

    # Scale new audio data to 16-bit integer range (-32768 to 32767)
    new_audio_data_int16 = (audio_chunk.data * (2**15 - 1)).astype(np.int16)

    # Open the existing WAV file in read mode to get parameters and current data
    with wave.open(str(filepath.absolute()), "rb") as infile:
        current_params = infile.getparams()
        current_frames = infile.readframes(infile.getnframes())

    # Ensure the new audio data matches the existing file's parameters
    # This is a critical step to avoid corrupting the WAV file
    # You might want to add more robust error handling or resampling here
    # if the parameters don't match exactly.
    existing_nchannels, existing_sampwidth, existing_framerate, *_ = current_params

    if (
        existing_nchannels != audio_chunk.number_of_channels
        or existing_sampwidth != 2  # Assuming 16-bit WAV files
        or existing_framerate != audio_chunk.framerate
    ):
        logger.warning(
            f"AudioChunk parameters ({audio_chunk.number_of_channels} ch, "
            f"{audio_chunk.framerate} Hz) do not match existing WAV file "
            f"({existing_nchannels} ch, {existing_framerate} Hz). "
            "This might lead to a corrupted file if not handled correctly. "
            "Attempting to proceed, but consider resample/reformat."
        )

    # Concatenate the existing and new audio data
    combined_audio_bytes = current_frames + new_audio_data_int16.tobytes()

    # Rewrite the entire WAV file with the combined data
    with wave.open(str(filepath.absolute()), "wb") as outfile:
        outfile.setnchannels(existing_nchannels)
        outfile.setsampwidth(existing_sampwidth)
        outfile.setframerate(existing_framerate)
        outfile.writeframes(combined_audio_bytes)
