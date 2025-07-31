import json
import logging
import asyncio
from typing import Set
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

from models.session import TranscriptionSession
from services.audio_processor import SessionAudioProcessor
from services.transcription_service import GlobalTranscriptionManager

logger = logging.getLogger(__name__)

class WebRTCConnectionHandler:
    """Handles individual WebRTC connections with per-session isolation"""
    
    def __init__(self, websocket, transcription_manager: GlobalTranscriptionManager):
        self.websocket = websocket
        self.transcription_manager = transcription_manager
        self.session = None
        self.audio_processor = None
        self.transcription_service = None
        self.peer_connection = None
        
        logger.info(f"New WebRTC connection handler created for {websocket.remote_address}")
    
    async def initialize_session(self):
        """Initialize a new transcription session for this connection"""
        self.session = TranscriptionSession()
        self.audio_processor = SessionAudioProcessor(self.session)
        self.transcription_service = self.transcription_manager.create_session_service(self.session)
        
        logger.info(f"Initialized session {self.session.session_id[:8]} for connection {self.websocket.remote_address}")
    
    async def handle_signaling_message(self, message: str):
        """Handle WebRTC signaling messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "offer":
                await self._handle_offer(data)
            elif message_type == "ice_candidate":
                await self._handle_ice_candidate(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling signaling message: {e}")
    
    async def _handle_offer(self, data):
        """Handle SDP offer from client"""
        logger.info(f"Received offer for session {self.session.session_id[:8]}")

        # Create peer connection
        self.peer_connection = RTCPeerConnection()

        # Set up audio track handler
        @self.peer_connection.on("track")
        async def on_track(track):
            logger.info(f"Session {self.session.session_id[:8]}: Received track: {track.kind}")

            if track.kind == "audio":
                await self._process_audio_track(track)

        # Set remote description (offer)
        offer = RTCSessionDescription(sdp=data["sdp"]["sdp"], type=data["sdp"]["type"])
        await self.peer_connection.setRemoteDescription(offer)

        # Create answer
        answer = await self.peer_connection.createAnswer()
        await self.peer_connection.setLocalDescription(answer)

        # Send answer back to client
        response = {
            "type": "answer",
            "sdp": {
                "sdp": self.peer_connection.localDescription.sdp,
                "type": self.peer_connection.localDescription.type
            },
        }

        await self.websocket.send(json.dumps(response))
        logger.info(f"Sent answer for session {self.session.session_id[:8]}")
        
    def _parse_candidate(self, candidate_str):
        parts = candidate_str.split()

        if len(parts) == 0:
            return None

        return {
            "foundation": parts[0].split(":")[1],
            "component": int(parts[1]),
            "protocol": parts[2].lower(),
            "priority": int(parts[3]),
            "ip": parts[4],
            "port": int(parts[5]),
            "type": parts[7],
        }

    async def _handle_ice_candidate(self, data):
        """Handle ICE candidate from client"""
        if self.peer_connection:
            try:
                parsed = self._parse_candidate(data["candidate"]["candidate"])

                if parsed is None:
                    # No more candidates
                    await self.peer_connection.addIceCandidate(None)
                    return

                candidate = RTCIceCandidate(
                    foundation=parsed["foundation"],
                    component=parsed["component"],
                    protocol=parsed["protocol"],
                    priority=parsed["priority"],
                    ip=parsed["ip"],
                    port=parsed["port"],
                    type=parsed["type"],
                    sdpMid=data["candidate"]["sdpMid"],
                    sdpMLineIndex=data["candidate"]["sdpMLineIndex"]
                )
                
                await self.peer_connection.addIceCandidate(candidate)
                logger.debug(f"Added ICE candidate for session {self.session.session_id[:8]}")
            except Exception as e:
                logger.error(f"Error adding ICE candidate: {e}")
    
    async def _process_audio_track(self, track):
        """Process incoming audio frames from WebRTC track"""
        try:
            while True:
                frame = await track.recv()
                
                # Process audio frame
                audio_array = self.audio_processor.process_frame(frame)
                
                # Convert to bytes for transcription
                if len(audio_array) > 0:
                    audio_bytes = audio_array.tobytes()
                    
                    # Process transcription
                    transcription = self.transcription_service.process_audio_chunk(audio_bytes)
                    
                    # Optionally send transcription back to client
                    if transcription:
                        await self._send_transcription_update(transcription)
        
        except Exception as e:
            logger.error(f"Error processing audio track for session {self.session.session_id[:8]}: {e}")
        
        finally:
            # Finalize session when audio stream ends
            await self._finalize_session()
    
    async def _send_transcription_update(self, text: str):
        """Send transcription update to client"""
        try:
            message = {
                "type": "transcription",
                "data": {
                    "text": text,
                    "session_id": self.session.session_id,
                    "timestamp": self.session.transcription_buffer[-1]["timestamp"]
                }
            }
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent transcription update for session {self.session.session_id[:8]}")
        
        except Exception as e:
            logger.error(f"Error sending transcription update: {e}")
    
    async def _finalize_session(self):
        """Finalize the transcription session"""
        if self.session and self.session.is_active:
            logger.info(f"Finalizing session {self.session.session_id[:8]}")
            
            # Save audio file
            if self.audio_processor:
                audio_file = self.audio_processor.save_session_audio()
                if audio_file:
                    logger.info(f"Session {self.session.session_id[:8]} audio saved to: {audio_file}")
            
            # Finalize transcription
            final_transcription = self.transcription_manager.finalize_session(self.session.session_id)
            if final_transcription:
                logger.info(f"Session {self.session.session_id[:8]} final transcription: {final_transcription}")
                
                # Send final transcription to client
                await self._send_final_transcription(final_transcription)
    
    async def _send_final_transcription(self, final_text: str):
        """Send final transcription result to client"""
        try:
            message = {
                "type": "final_transcription",
                "data": {
                    "text": final_text,
                    "session_id": self.session.session_id,
                    "metadata": self.session.metadata
                }
            }
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent final transcription for session {self.session.session_id[:8]}")
        
        except Exception as e:
            logger.error(f"Error sending final transcription: {e}")
    
    async def cleanup(self):
        """Clean up resources for this connection"""
        if self.peer_connection:
            await self.peer_connection.close()
        
        if self.session and self.session.is_active:
            await self._finalize_session()
        
        logger.info(f"Cleaned up WebRTC connection handler for session {self.session.session_id[:8] if self.session else 'unknown'}")

class WebRTCServer:
    """Main WebRTC server handling multiple concurrent sessions"""
    
    def __init__(self):
        self.connections: Set[WebRTCConnectionHandler] = set()
        self.transcription_manager = GlobalTranscriptionManager()
        logger.info("WebRTC server initialized")
    
    async def handle_client(self, websocket):
        """Handle new WebSocket connection"""
        handler = WebRTCConnectionHandler(websocket, self.transcription_manager)
        await handler.initialize_session()
        
        self.connections.add(handler)
        logger.info(f"New client connected: {websocket.remote_address}, Session: {handler.session.session_id[:8]}")

        try:
            async for message in websocket:
                await handler.handle_signaling_message(message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        
        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
        
        finally:
            await handler.cleanup()
            self.connections.discard(handler)
            logger.info(f"Connection handler removed for session {handler.session.session_id[:8] if handler.session else 'unknown'}")
    
    async def cleanup_inactive_sessions(self):
        """Periodic cleanup of inactive sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                self.transcription_manager.cleanup_inactive_sessions()
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")
    
    def get_active_sessions_count(self) -> int:
        """Get number of active sessions"""
        return len(self.transcription_manager.active_sessions)