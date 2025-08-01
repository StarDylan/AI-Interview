import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from vosk import Model, KaldiRecognizer

from config.settings import VOSK_MODEL_PATH, TARGET_SAMPLE_RATE, TRANSCRIPTIONS_DIR
from models.session import TranscriptionSession

logger = logging.getLogger(__name__)

class SessionTranscriptionService:
    """Handles speech-to-text transcription with per-session isolation"""
    
    def __init__(self, session: TranscriptionSession):
        self.session = session
        self.model: Optional[Any] = None
        self.recognizer: Optional[Any] = None
        self.audio_buffer = bytearray()
        self.transcriptions_dir = Path(TRANSCRIPTIONS_DIR)
        
        # Create transcriptions directory
        self.transcriptions_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Vosk model and recognizer
        self._initialize_vosk()
        
        logger.info(f"Transcription service initialized for session {self.session.session_id[:8]}")
    
    def _initialize_vosk(self):
        """Initialize Vosk model and recognizer for this session"""
        try:
            if not os.path.exists(VOSK_MODEL_PATH):
                raise FileNotFoundError(f"Vosk model not found at {VOSK_MODEL_PATH}")
            
            self.model = Model(str(VOSK_MODEL_PATH))
            self.recognizer = KaldiRecognizer(self.model, TARGET_SAMPLE_RATE)
            self.recognizer.SetWords(True)
            self.recognizer.SetPartialWords(True)
            
            logger.info(f"Vosk model loaded for session {self.session.session_id[:8]}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vosk model for session {self.session.session_id[:8]}: {e}")
            raise
    
    def process_audio_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Process audio chunk and return transcription if available"""
        if not self.session.is_active:
            logger.warning(f"Attempted to process audio for inactive session {self.session.session_id[:8]}")
            return None
        
        if not self.recognizer:
            logger.error(f"Recognizer not initialized for session {self.session.session_id[:8]}")
            return None
        
        try:
            # Process audio with Vosk
            if self.recognizer.AcceptWaveform(audio_chunk):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                
                if text:
                    self.session.add_transcription(text)
                    logger.info(f"Session {self.session.session_id[:8]} transcription: {text}")
                    return text
            
            # Check for partial results
            partial_result = json.loads(self.recognizer.PartialResult())
            partial_text = partial_result.get("partial", "").strip()
            
            if partial_text:
                logger.debug(f"Session {self.session.session_id[:8]} partial: {partial_text}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing audio chunk for session {self.session.session_id[:8]}: {e}")
            return None
    
    def finalize_transcription(self) -> Optional[str]:
        """Get final transcription result and save to file"""
        if not self.recognizer:
            return None
        
        try:
            # Get final result from Vosk
            final_result = json.loads(self.recognizer.FinalResult())
            final_text = final_result.get("text", "").strip()
            
            if final_text:
                self.session.add_transcription(final_text)
                logger.info(f"Session {self.session.session_id[:8]} final transcription: {final_text}")
            
            # Save complete transcription to file
            self._save_transcription_file()
            
            return self.session.get_full_transcription()
            
        except Exception as e:
            logger.error(f"Error finalizing transcription for session {self.session.session_id[:8]}: {e}")
            return None
    
    def _save_transcription_file(self) -> Optional[Path]:
        """Save transcription data to JSON file"""
        try:
            timestamp = self.session.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"transcription_{timestamp}_{self.session.session_id[:8]}.json"
            filepath = self.transcriptions_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.session.get_transcription_json())
            
            # Also save plain text version
            text_filename = f"transcription_{timestamp}_{self.session.session_id[:8]}.txt"
            text_filepath = self.transcriptions_dir / text_filename
            
            with open(text_filepath, 'w', encoding='utf-8') as f:
                f.write(self.session.get_full_transcription())
            
            logger.info(f"Session {self.session.session_id[:8]} transcription saved to: {filepath}")
            
            # Update session metadata
            self.session.metadata.update({
                "transcription_file": str(filepath),
                "transcription_text_file": str(text_filepath),
                "total_transcriptions": len(self.session.transcription_buffer)
            })
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving transcription file for session {self.session.session_id[:8]}: {e}")
            return None

class GlobalTranscriptionManager:
    """Manages transcription services across multiple sessions"""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionTranscriptionService] = {}
        logger.info("Global transcription manager initialized")
    
    def create_session_service(self, session: TranscriptionSession) -> SessionTranscriptionService:
        """Create a new transcription service for a session"""
        service = SessionTranscriptionService(session)
        self.active_sessions[session.session_id] = service
        logger.info(f"Created transcription service for session {session.session_id[:8]}")
        return service
    
    def get_session_service(self, session_id: str) -> Optional[SessionTranscriptionService]:
        """Get transcription service for a session"""
        return self.active_sessions.get(session_id)
    
    def finalize_session(self, session_id: str) -> Optional[str]:
        """Finalize transcription for a session and clean up"""
        service = self.active_sessions.get(session_id)
        if service:
            result = service.finalize_transcription()
            service.session.finalize()
            del self.active_sessions[session_id]
            logger.info(f"Finalized and removed session {session_id[:8]}")
            return result
        return None
    
    def cleanup_inactive_sessions(self):
        """Remove services for inactive sessions"""
        inactive_sessions = [
            session_id for session_id, service in self.active_sessions.items()
            if not service.session.is_active
        ]
        
        for session_id in inactive_sessions:
            self.finalize_session(session_id)
        
        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")