import os
import wave
import logging
import numpy as np
import scipy.signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from av.audio.frame import AudioFrame

from config.settings import (
    SAMPLE_RATE, NUM_CHANNELS, SAMPLE_WIDTH, TARGET_SAMPLE_RATE,
    AUDIO_RECORDINGS_DIR
)
from models.session import TranscriptionSession

logger = logging.getLogger(__name__)

def resample_audio(pcm_data: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    """Resample audio to target sample rate"""
    resampled = scipy.signal.resample_poly(pcm_data, target_rate, orig_rate).astype(np.int16)
    return resampled

def stereo_to_mono(stereo_pcm: np.ndarray) -> np.ndarray:
    """Convert stereo audio to mono"""
    if len(stereo_pcm.shape) > 1 and stereo_pcm.shape[1] == 2:
        mono_data = stereo_pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)
    else:
        mono_data = stereo_pcm.astype(np.int16)
    return mono_data

class SessionAudioProcessor:
    """Process incoming audio frames with per-session isolation"""

    def __init__(self, session: TranscriptionSession, save_audio: bool = True, output_dir: str = AUDIO_RECORDINGS_DIR):
        self.session = session
        self.frame_count = 0
        self.save_audio = save_audio
        self.output_dir = Path(output_dir)
        self.sample_rate = None
        self.channels = None

        # Create output directory if it doesn't exist
        if self.save_audio:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_frame(self, frame: AudioFrame) -> np.ndarray:
        """Process audio frame and add to session buffer"""
        if not self.session.is_active:
            logger.warning(f"Attempted to process frame for inactive session {self.session.session_id[:8]}")
            return np.array([])

        # Convert frame to numpy array
        audio_array = frame.to_ndarray()
        
        # Convert to mono if stereo
        if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
            audio_array = stereo_to_mono(audio_array)
        
        # Resample if necessary
        if frame.sample_rate != TARGET_SAMPLE_RATE:
            audio_array = resample_audio(audio_array, frame.sample_rate, TARGET_SAMPLE_RATE)

        # Initialize session audio properties on first frame
        if self.sample_rate is None:
            self.sample_rate = TARGET_SAMPLE_RATE
            self.channels = 1
            logger.info(f"Session {self.session.session_id[:8]} initialized with sample rate: {self.sample_rate}")

        # Add to session buffer
        if self.save_audio:
            self.session.audio_buffer.append(audio_array)

        self.frame_count += 1

        # Log progress every 100 frames
        if self.frame_count % 100 == 0:
            logger.debug(
                f"Session {self.session.session_id[:8]}: Processed {self.frame_count} frames. "
                f"Shape: {audio_array.shape}, Sample rate: {self.sample_rate}"
            )

        return audio_array

    def save_session_audio(self, filename: Optional[str] = None) -> Optional[Path]:
        """Save accumulated audio buffer to WAV file"""
        if not self.save_audio or not self.session.audio_buffer:
            logger.warning(f"No audio data to save for session {self.session.session_id[:8]}")
            return None

        if filename is None:
            timestamp = self.session.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"audio_{timestamp}_{self.session.session_id[:8]}.wav"

        filepath = self.output_dir / filename

        try:
            # Concatenate all audio frames
            full_audio = np.concatenate(self.session.audio_buffer, axis=0)

            # Convert to 16-bit PCM format
            if full_audio.dtype != np.int16:
                if full_audio.dtype in [np.float32, np.float64]:
                    full_audio = np.clip(full_audio, -1.0, 1.0)
                    full_audio = (full_audio * 32767).astype(np.int16)
                else:
                    full_audio = full_audio.astype(np.int16)

            # Save as WAV file
            with wave.open(str(filepath), "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(SAMPLE_WIDTH)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(full_audio.tobytes())

            duration = len(full_audio) / self.sample_rate
            logger.info(f"Session {self.session.session_id[:8]} audio saved to: {filepath}")
            logger.info(f"Duration: {duration:.2f} seconds, Frames: {len(self.session.audio_buffer)}")
            
            # Add metadata to session
            self.session.metadata.update({
                "audio_file": str(filepath),
                "duration_seconds": duration,
                "total_frames": len(self.session.audio_buffer),
                "sample_rate": self.sample_rate,
                "channels": self.channels
            })
            
            return filepath

        except Exception as e:
            logger.error(f"Error saving audio file for session {self.session.session_id[:8]}: {e}")
            return None