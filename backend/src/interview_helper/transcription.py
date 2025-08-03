import json
import logging
from typing import AsyncGenerator, Optional
from vosk import Model, KaldiRecognizer
from pathlib import Path

logger = logging.getLogger(__name__)

# Global model and recognizer instances (loaded via FastAPI lifespan)
_model: Optional[Model] = None
_sample_rate: int = 16000


def initialize_vosk_model(model_path: Path, sample_rate: int):
    """Initialize Vosk model (called from FastAPI lifespan)"""
    global _model, _sample_rate

    try:
        _model = Model(str(model_path))
        _sample_rate = sample_rate
        logger.info(f"Vosk model loaded from {model_path}")

    except Exception as e:
        logger.error(f"Failed to initialize Vosk model: {e}")
        raise


def create_recognizer() -> Optional[KaldiRecognizer]:
    """Create a new recognizer instance for a session"""
    if not _model:
        logger.error("Vosk model not initialized")
        return None

    try:
        recognizer = KaldiRecognizer(_model, _sample_rate)
        recognizer.SetWords(True)
        recognizer.SetPartialWords(True)
        return recognizer
    except Exception as e:
        logger.error(f"Failed to create recognizer: {e}")
        return None


async def transcribe_stream(
    chunk: bytes, recognizer: KaldiRecognizer
) -> AsyncGenerator[str, None]:
    """
    Yield partial transcripts from audio chunks.
    Must be swappable (mockable in tests or switchable between providers).
    """
    try:
        if recognizer.AcceptWaveform(chunk):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                yield text

        # Also yield partial results for real-time feedback
        partial_result = json.loads(recognizer.PartialResult())
        partial_text = partial_result.get("partial", "").strip()
        if partial_text:
            # Mark as partial by prefixing (consumers can handle this)
            yield f"PARTIAL:{partial_text}"

    except Exception as e:
        logger.error(f"Error processing audio chunk: {e}")


def finalize_transcription(recognizer: KaldiRecognizer) -> Optional[str]:
    """Get final transcription result"""
    try:
        final_result = json.loads(recognizer.FinalResult())
        return final_result.get("text", "").strip()
    except Exception as e:
        logger.error(f"Error getting final result: {e}")
        return None


# Mock functions for testing
async def mock_transcribe_stream(
    chunk: bytes, responses: Optional[list[str]] = None
) -> AsyncGenerator[str, None]:
    """Mock transcription function for testing"""
    responses = responses or ["Hello", "world", "this is a test"]

    # Simple mock - just yield responses based on chunk count
    import hashlib

    chunk_hash = hashlib.md5(chunk).hexdigest()
    index = int(chunk_hash, 16) % len(responses)
    yield responses[index]
