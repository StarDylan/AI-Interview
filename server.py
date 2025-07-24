import asyncio
import json
import logging
import websockets
import numpy as np
import wave
import os
from datetime import datetime
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from vosk import Model, KaldiRecognizer
from av.audio.frame import AudioFrame
from typing import cast
from streamz import Stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import streamz

vosk_model = Model("vosk_models/vosk-model-small-en-us-0.15")  # Download from: https://alphacephei.com/vosk/models
recognizer = KaldiRecognizer(vosk_model, 48000)

recognizer.SetWords(True)
recognizer.SetPartialWords(True)

import json
import wave
import os

# You may need to adjust these based on your actual audio settings
SAMPLE_RATE = 48000  # Hz
NUM_CHANNELS = 1
SAMPLE_WIDTH = 2     # 2 bytes for 16-bit audio



def transcribe(audio_chunk, text_file_path="transcription.txt", audio_file_path="transcription.wav"):
    # Write text result
    text = []
    if recognizer.AcceptWaveform(audio_chunk):
        result = json.loads(recognizer.Result())
        text = result.get("text", "")
        with open(text_file_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Transcription result: {result}")

    # Write audio chunk to .wav file
    if not os.path.exists(audio_file_path):
        # Create and write header if file doesn't exist
        with wave.open(audio_file_path, 'wb') as wf:
            wf.setnchannels(NUM_CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_chunk)
    else:
        # Append audio to existing .wav file
        with wave.open(audio_file_path, 'rb') as rf:
            params = rf.getparams()
            existing_frames = rf.readframes(rf.getnframes())

        with wave.open(audio_file_path, 'wb') as wf:
            wf.setparams(params)
            wf.writeframes(existing_frames + audio_chunk)

    return {"text": text, "raw": audio_chunk}

SAMPLE_RATE = 48000
MIN_DURATION = 5  # seconds
BYTES_PER_SAMPLE = 2
MIN_BYTES = int(SAMPLE_RATE * BYTES_PER_SAMPLE * MIN_DURATION)

# Start with a `bytearray` buffer
def buffer_audio(buffer: bytearray, chunk: bytes):
    buffer.extend(chunk)

    if len(buffer) >= MIN_BYTES:
        complete = bytes(buffer)      # convert to flat bytes
        buffer.clear()                # reset the buffer
        return buffer, complete       # emit valid audio bytes
    else:
        return buffer, None           # not enough yet, emit nothing

live_audio_stream = streamz.Stream()
buffered = live_audio_stream.accumulate(buffer_audio, start=bytearray(),returns_state=True).filter(lambda x: x is not None)
transcripts = buffered.map(transcribe)
transcripts.map(lambda x: x["text"]).sink(lambda x: print(x, end=""))

# open file
# transcripts.map(lambda x: x["raw"]).sink(lambda x: print(f"Raw audio chunk received: {len(x)} bytes"))
# save raw audio chunks to a file
# Note: This is just an example, you can modify the sink to save to a file
# or process the audio chunks as needed.


import numpy as np
import scipy.signal

def resample_audio(pcm_data: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    resampled = scipy.signal.resample_poly(pcm_data, target_rate, orig_rate).astype(np.int16)
    return resampled

def stereo_to_mono(stereo_pcm: np.ndarray) -> np.ndarray:
    mono_data = stereo_pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)
    return mono_data

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


    def process_frame(self, frame: AudioFrame):
        """Process audio frame - convert to numpy array for analysis"""
        # Convert frame to numpy array
        audio_array = resample_audio(frame.to_ndarray(), 
                       orig_rate=frame.sample_rate, 
                       target_rate=16000)

        audio_array = stereo_to_mono(audio_array)

        # Emit raw bytes for Vosk (expects PCM bytes)
        live_audio_stream.emit(audio_array.tobytes())

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

        # Vosk finalResult
        result = json.loads(recognizer.FinalResult())
        text = result.get("text", "")
        logger.info(f"Final transcription result: {text}")


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

    logger.info("Starting WebRTC server on ws://localhost:3000")

    import ssl


    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Path relative to your project root
    cert_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'cert')
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')

    ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)

    # Start WebSocket server for signaling
    async with websockets.serve(server.handle_client, "0.0.0.0", 3000,
        ssl=ssl_context):
        logger.info("Server started. Waiting for connections...")
        # Keep server running
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
