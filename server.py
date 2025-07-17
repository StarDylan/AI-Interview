import asyncio
import json
import logging
import websockets
import numpy as np
import wave
import os
from datetime import datetime
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioProcessor:
    """Process incoming audio frames"""

    def __init__(self, save_audio=True, output_dir="audio_recordings"):
        self.frame_count = 0
        self.save_audio = save_audio
        self.output_dir = output_dir
        self.audio_buffer = []
        self.sample_rate = None
        self.channels = None
        self.current_session_id = None

        # Create output directory if it doesn't exist
        if self.save_audio:
            os.makedirs(self.output_dir, exist_ok=True)

    def start_new_session(self):
        """Start a new audio recording session"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_id = f"audio_{timestamp}"
        self.audio_buffer = []
        logger.info(f"Started new audio session: {self.current_session_id}")

    def process_frame(self, frame):
        """Process audio frame - convert to numpy array for analysis"""
        # Convert frame to numpy array
        audio_array = frame.to_ndarray()

        # Initialize session on first frame
        if self.current_session_id is None:
            self.sample_rate = frame.sample_rate
            self.channels = audio_array.shape[1] if len(audio_array.shape) > 1 else 1
            self.start_new_session()

        # Save audio data to buffer if enabled
        if self.save_audio:
            self.audio_buffer.append(audio_array)

        self.frame_count += 1

        # Log basic info every 100 frames
        if self.frame_count % 100 == 0:
            logger.info(
                f"Processed {self.frame_count} frames. "
                f"Shape: {audio_array.shape}, "
                f"Sample rate: {frame.sample_rate}"
            )

        return audio_array

    def save_audio_to_file(self, filename=None):
        """Save accumulated audio buffer to WAV file"""
        if not self.save_audio or not self.audio_buffer:
            logger.warning("No audio data to save")
            return None

        if filename is None:
            filename = f"{self.current_session_id}.wav"

        filepath = os.path.join(self.output_dir, filename)

        try:
            # Concatenate all audio frames
            full_audio = np.concatenate(self.audio_buffer, axis=0)

            # Convert to 16-bit PCM format
            if full_audio.dtype != np.int16:
                # Normalize to [-1, 1] if needed
                if full_audio.dtype == np.float32 or full_audio.dtype == np.float64:
                    full_audio = np.clip(full_audio, -1.0, 1.0)
                    full_audio = (full_audio * 32767).astype(np.int16)
                else:
                    full_audio = full_audio.astype(np.int16)

            # Save as WAV file
            with wave.open(filepath, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(full_audio.tobytes())
                print(self.sample_rate)
                print(self.channels)

            logger.info(f"Audio saved to: {filepath}")
            logger.info(f"Duration: {len(full_audio) / self.sample_rate:.2f} seconds")
            return filepath

        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            return None

    def finalize_session(self):
        """Finalize current session and save audio"""
        if self.current_session_id and self.audio_buffer:
            filepath = self.save_audio_to_file()
            # Clear buffer after saving
            self.audio_buffer = []
            self.current_session_id = None
            return filepath
        return None


class WebRTCServer:
    def __init__(self):
        self.connections = set()
        self.audio_processor = AudioProcessor()

    async def handle_client(self, websocket):
        """Handle WebSocket connection for signaling"""
        logger.info(f"New client connected: {websocket.remote_address}")
        self.connections.add(websocket)

        try:
            async for message in websocket:
                await self.handle_signaling_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.connections.discard(websocket)

    async def handle_signaling_message(self, websocket, message):
        """Handle signaling messages (SDP offers, ICE candidates)"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "offer":
                await self.handle_offer(websocket, data)
            elif message_type == "ice-candidate":
                await self.handle_ice_candidate(websocket, data)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def handle_offer(self, websocket, data):
        """Handle SDP offer from client"""
        logger.info("Received offer from client")

        # Create peer connection
        pc = RTCPeerConnection()

        # Set up audio track handler
        @pc.on("track")
        async def on_track(track):
            logger.info(f"Received track: {track.kind}")

            if track.kind == "audio":
                # Process incoming audio frames
                while True:
                    try:
                        frame = await track.recv()
                        self.audio_processor.process_frame(frame)
                    except Exception as e:
                        logger.error(f"Error processing audio frame: {e}")
                        break

                # Finalize session when audio stream ends
                logger.info("Audio stream ended, finalizing session...")
                saved_file = self.audio_processor.finalize_session()
                if saved_file:
                    logger.info(f"Audio session saved to: {saved_file}")
                else:
                    logger.warning("No audio data was saved")

        # Set remote description (offer)
        offer = RTCSessionDescription(sdp=data["sdp"]["sdp"], type=data["sdp"]["type"])
        await pc.setRemoteDescription(offer)

        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Send answer back to client
        response = {
            "type": "answer",
            "sdp": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type},
        }

        await websocket.send(json.dumps(response))
        logger.info("Sent answer to client")

        # Store peer connection for ICE candidates
        websocket.pc = pc

    async def handle_ice_candidate(self, websocket, data):
        """Handle ICE candidate from client"""
        if hasattr(websocket, "pc"):
            candidate = RTCIceCandidate(
                component=data["candidate"]["component"],
                foundation=data["candidate"]["foundation"],
                ip=data["candidate"]["address"],
                port=data["candidate"]["port"],
                priority=data["candidate"]["priority"],
                protocol=data["candidate"]["protocol"],
                type=data["candidate"]["type"],
            )
            await websocket.pc.addIceCandidate(candidate)
            logger.info("Added ICE candidate")


async def main():
    """Start the WebRTC server"""
    server = WebRTCServer()

    logger.info("Starting WebRTC server on ws://localhost:8765")

    # Start WebSocket server for signaling
    async with websockets.serve(server.handle_client, "localhost", 8765):
        logger.info("Server started. Waiting for connections...")
        # Keep server running
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
