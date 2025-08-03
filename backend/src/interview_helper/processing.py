import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessedText:
    """Result of text processing"""

    word_count: int


def process_text(text: str) -> ProcessedText:
    """
    Process text into useful data (e.g., NLP).
    Must be swappable and testable independently.
    """
    if not text or not text.strip():
        return ProcessedText(word_count=0)

    word_count = len(text.split())

    return ProcessedText(word_count=word_count)
