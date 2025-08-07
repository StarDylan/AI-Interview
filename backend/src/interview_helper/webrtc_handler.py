import json
import logging
from typing import Optional, Callable, Awaitable
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

from interview_helper.session import Project, SessionManager
from interview_helper.transcription import (
    transcribe_stream,
    create_recognizer,
    finalize_transcription,
)
from interview_helper.processing import process_text
from interview_helper.messages import WebRTCMessage

logger = logging.getLogger(__name__)

# Hook type definitions
OnOfferHook = Callable[[str, dict], Awaitable[None]]
OnAudioChunkHook = Callable[[str, bytes], Awaitable[None]]


def parse_candidate(candidate_str: str) -> Optional[dict]:
    """Parse ICE candidate string into components"""
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


async def handle_offer(
    user_id: str, offer_data: dict, session: Project
) -> Optional[dict]:
    """Handle WebRTC offer - returns answer data"""
    try:
        logger.info(f"Handling offer for user {user_id}")

        # Create peer connection
        peer_connection = RTCPeerConnection()

        # Store peer connection in session metadata
        session.metadata["peer_connection"] = peer_connection
        session.metadata["recognizer"] = create_recognizer()

        # Set up audio track handler
        @peer_connection.on("track")
        async def on_track(track):
            logger.info(f"User {user_id}: Received track: {track.kind}")

            if track.kind == "audio":
                await process_audio_track(user_id, track, session)

        # Set remote description (offer)
        offer = RTCSessionDescription(
            sdp=offer_data["sdp"]["sdp"], type=offer_data["sdp"]["type"]
        )
        await peer_connection.setRemoteDescription(offer)

        # Create answer
        answer = await peer_connection.createAnswer()
        await peer_connection.setLocalDescription(answer)

        # Return answer data
        return {
            "type": "answer",
            "sdp": {
                "sdp": peer_connection.localDescription.sdp,
                "type": peer_connection.localDescription.type,
            },
        }

    except Exception as e:
        logger.error(f"Error handling offer for user {user_id}: {e}")
        await session.send_error("offer_error", str(e))
        return None


async def handle_ice_candidate(user_id: str, candidate_data: dict, session: Project):
    """Handle ICE candidate"""
    peer_connection = session.metadata.get("peer_connection")
    if not peer_connection:
        logger.error(f"No peer connection for user {user_id}")
        return

    try:
        parsed = parse_candidate(candidate_data["candidate"]["candidate"])

        if parsed is None:
            # No more candidates
            await peer_connection.addIceCandidate(None)
            return

        candidate = RTCIceCandidate(
            foundation=str(parsed["foundation"]),
            component=parsed["component"],
            protocol=str(parsed["protocol"]),
            priority=parsed["priority"],
            ip=str(parsed["ip"]),
            port=parsed["port"],
            type=str(parsed["type"]),
            sdpMid=candidate_data["candidate"]["sdpMid"],
            sdpMLineIndex=candidate_data["candidate"]["sdpMLineIndex"],
        )

        await peer_connection.addIceCandidate(candidate)
        logger.debug(f"Added ICE candidate for user {user_id}")

    except Exception as e:
        logger.error(f"Error adding ICE candidate for user {user_id}: {e}")
        await session.send_error("ice_candidate_error", str(e))


async def process_audio_track(user_id: str, track, session: Project):
    """Process incoming audio frames from WebRTC track"""
    recognizer = session.metadata.get("recognizer")
    if not recognizer:
        logger.error(f"No recognizer for user {user_id}")
        return

    try:
        while True:
            frame = await track.recv()

            # Convert frame to audio data (simplified - would need proper conversion)
            # This is a placeholder - actual implementation would convert AudioFrame to bytes
            audio_bytes = frame.to_ndarray().astype("int16").tobytes()

            # Process transcription
            async for transcript in transcribe_stream(audio_bytes, recognizer):
                if transcript.startswith("PARTIAL:"):
                    # Partial transcript
                    text = transcript[8:]  # Remove "PARTIAL:" prefix
                    await session.send_transcription(text, is_partial=True)
                else:
                    # Final transcript
                    session.add_transcription(transcript, is_partial=False)
                    await session.send_transcription(transcript, is_partial=False)

                    # Process the text
                    processed = process_text(transcript)
                    logger.info(f"User {user_id}: Processed text - {processed}")

    except Exception as e:
        logger.error(f"Error processing audio track for user {user_id}: {e}")

    finally:
        # Finalize session when audio stream ends
        await finalize_session(user_id, session)


async def finalize_session(user_id: str, session: Project):
    """Finalize the session"""
    if not session.is_active:
        return

    logger.info(f"Finalizing session for user {user_id}")

    try:
        # Get final transcription
        recognizer = session.metadata.get("recognizer")
        if recognizer:
            try:
                final_text = finalize_transcription(recognizer)
                if final_text:
                    session.add_transcription(final_text, is_partial=False)
                    await session.send_transcription(final_text, is_partial=False)
            except Exception as e:
                logger.error(f"Error finalizing transcription for user {user_id}: {e}")
                await session.send_error(
                    "finalization_error", f"Failed to finalize transcription: {e}"
                )

        # Close peer connection with proper error handling
        peer_connection = session.metadata.get("peer_connection")
        if peer_connection:
            try:
                await peer_connection.close()
                logger.debug(f"Closed peer connection for user {user_id}")
            except Exception as e:
                logger.error(f"Error closing peer connection for user {user_id}: {e}")

    except Exception as e:
        logger.error(
            f"Unexpected error during session finalization for user {user_id}: {e}"
        )
    finally:
        # Always deactivate session, even if cleanup fails
        session.deactivate()


# Hook implementations
async def on_offer(user_id: str, offer_data: dict, session_manager: SessionManager):
    """Hook: Handle WebRTC offer"""
    session = session_manager.get_session_by_user(user_id)
    if not session:
        logger.error(f"No session found for user {user_id}")
        return

    answer_data = await handle_offer(user_id, offer_data, session)
    if answer_data:
        await session.send(WebRTCMessage(type="answer", data=answer_data))


async def on_audio_chunk(user_id: str, chunk: bytes, session_manager: SessionManager):
    """Hook: Handle audio chunk"""
    session = session_manager.route_audio_chunk(user_id, chunk)
    if session:
        logger.debug(f"Processed audio chunk for user {user_id}")


def setup_webrtc_hooks(session_manager: SessionManager):
    """Setup WebRTC-specific hooks"""

    async def webrtc_on_connect(user_id: str, send_func):
        # Create session for user
        session_manager.create_session(user_id, send_func)
        logger.info(f"Created WebRTC session for user {user_id}")

    async def webrtc_on_message(user_id: str, message: str):
        session = session_manager.get_session_by_user(user_id)
        if not session:
            logger.error(f"No session found for user {user_id}")
            return

        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "offer":
                answer_data = await handle_offer(user_id, data, session)
                if answer_data:
                    await session.send(WebRTCMessage(type="answer", data=answer_data))
            elif message_type == "ice_candidate":
                await handle_ice_candidate(user_id, data, session)
            else:
                logger.warning(f"Unknown WebRTC message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from user {user_id}")
        except Exception as e:
            logger.error(f"Error handling WebRTC message from user {user_id}: {e}")

    async def webrtc_on_disconnect(user_id: str):
        session = session_manager.get_session_by_user(user_id)
        if session:
            await finalize_session(user_id, session)
            # Remove session using the session_id
            removed = session_manager.remove_session(session.project_id)
            if removed:
                logger.info(f"Cleaned up WebRTC session for user {user_id}")
            else:
                logger.warning(f"Failed to remove session for user {user_id}")
        else:
            logger.warning(f"No session found to clean up for user {user_id}")

    return webrtc_on_connect, webrtc_on_message, webrtc_on_disconnect
