import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class TranscriptionSession:
    """Represents a single transcription session with isolated state"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    audio_buffer: list = field(default_factory=list)
    transcription_buffer: list = field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_transcription(self, text: str, timestamp: Optional[datetime] = None):
        """Add transcription text to session buffer"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.transcription_buffer.append({
            "text": text,
            "timestamp": timestamp.isoformat(),
            "session_id": self.session_id
        })
        logger.debug(f"Added transcription to session {self.session_id[:8]}: {text}")
    
    def get_full_transcription(self) -> str:
        """Get complete transcription text for this session"""
        return " ".join([item["text"] for item in self.transcription_buffer])
    
    def get_transcription_json(self) -> str:
        """Get transcription data as JSON"""
        return json.dumps({
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "transcriptions": self.transcription_buffer,
            "metadata": self.metadata
        }, indent=2)
    
    def finalize(self):
        """Mark session as complete"""
        self.is_active = False
        logger.info(f"Session {self.session_id[:8]} finalized with {len(self.transcription_buffer)} transcriptions")