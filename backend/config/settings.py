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
BASE_DIR = Path(__file__).parent.parent.parent
VOSK_MODEL_PATH = BASE_DIR / "backend" / "vosk_models" / "vosk-model-small-en-us-0.15"
CERT_DIR = BASE_DIR / "frontend" / "cert"
CERT_FILE = CERT_DIR / "cert.pem"
KEY_FILE = CERT_DIR / "key.pem"

# Output directories
AUDIO_RECORDINGS_DIR = "audio_recordings"
TRANSCRIPTIONS_DIR = "transcriptions"

# Derived settings
MIN_BYTES = int(TARGET_SAMPLE_RATE * BYTES_PER_SAMPLE * MIN_DURATION)