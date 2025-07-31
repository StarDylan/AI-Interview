import os
from pathlib import Path

# Audio processing settings
NUM_CHANNELS = 1
SAMPLE_WIDTH = 2
TARGET_SAMPLE_RATE = 48000
MIN_DURATION = 5
BYTES_PER_SAMPLE = 2

# Server settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 3000

# File paths
VOSK_MODEL_PATH = Path("vosk_models") / "vosk-model-small-en-us-0.15"

# Output directories
AUDIO_RECORDINGS_DIR = "audio_recordings"
TRANSCRIPTIONS_DIR = "transcriptions"

# Derived settings
MIN_BYTES = int(TARGET_SAMPLE_RATE * BYTES_PER_SAMPLE * MIN_DURATION)