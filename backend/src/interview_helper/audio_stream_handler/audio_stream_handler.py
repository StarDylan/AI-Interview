import logging
from typing import Optional
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.mediastreams import MediaStreamTrack
from av.audio.frame import AudioFrame

from interview_helper.audio_stream_handler.types import ICECandidate
from interview_helper.context_manager import SessionContext
from interview_helper.context_manager.resource_keys import (
    WEBSOCKET,
    WEBRTC_PEER_CONNECTION,
)
from interview_helper.context_manager.messages import WebRTCMessage

from interview_helper.audio_stream_handler.audio_utils import to_pcm

logger = logging.getLogger(__name__)


def handle_webrtc_message(ctx: SessionContext, message: WebRTCMessage):
    message_type = message.type

    if message_type == "offer":
        await handle_offer(ctx, message.data)
    elif message_type == "ice_candidate":
        await handle_ice_candidate(ctx, message.data)
    else:
        logger.warning(f"Unknown WebRTC message type: {message_type}")


async def handle_offer(ctx: SessionContext, offer_data: dict):
    """
    - We get notified of client's capabilities (codecs, media tracks).
    - Send the client our capabilities.
    """

    # TODO: Check there isn't already a RTC connection for this *project*.

    # Create peer connection
    peer_connection = RTCPeerConnection()

    @peer_connection.on("track")
    async def on_track(track: MediaStreamTrack):
        if track.kind == "audio":
            await audio_processing_task(track, ctx)

    # Set remote description (offer)
    offer = RTCSessionDescription(
        sdp=offer_data["sdp"]["sdp"], type=offer_data["sdp"]["type"]
    )
    await peer_connection.setRemoteDescription(offer)

    # Create answer
    answer = await peer_connection.createAnswer()
    await peer_connection.setLocalDescription(answer)

    websocket = await ctx.get(WEBSOCKET)

    await websocket.send_message(
        WebRTCMessage(
            type="answer",
            data={
                "sdp": {
                    "sdp": peer_connection.localDescription.sdp,
                    "type": peer_connection.localDescription.type,
                },
            },
        )
    )


async def handle_ice_candidate(ctx: SessionContext, candidate_data: dict):
    """Handle ICE candidate"""
    peer_connection = await ctx.get(WEBRTC_PEER_CONNECTION)

    parsed = parse_candidate(candidate_data["candidate"]["candidate"])

    if parsed is None:
        # No more candidates
        await peer_connection.addIceCandidate(None)
        return

    candidate = RTCIceCandidate(
        foundation=parsed.foundation,
        component=parsed.component,
        protocol=parsed.protocol,
        priority=parsed.priority,
        ip=parsed.ip,
        port=parsed.port,
        type=parsed.ice_type,
        sdpMid=candidate_data["candidate"]["sdpMid"],
        sdpMLineIndex=candidate_data["candidate"]["sdpMLineIndex"],
    )

    await peer_connection.addIceCandidate(candidate)


async def audio_processing_task(track: MediaStreamTrack, ctx: SessionContext):
    """Process incoming audio frames from WebRTC track and send to session context"""

    while True:
        frame = await track.recv()
        assert isinstance(frame, AudioFrame), "Incoming audio track is not a frame!"

        audio_array = to_pcm(frame)

        ctx.ingest_audio(audio_array)

    ## TODO: Add try finally here
    await finalize_session(ctx)


async def finalize_session(ctx: SessionContext):
    """Finalize the session"""

    peer_connection = await ctx.get(WEBRTC_PEER_CONNECTION)
    await peer_connection.close()


def parse_candidate(candidate_str: str) -> Optional[ICECandidate]:
    """Parse ICE candidate string into components"""
    parts = candidate_str.split()

    if len(parts) == 0:
        return None

    return ICECandidate(
        foundation=parts[0].split(":")[1],
        component=int(parts[1]),
        protocol=parts[2].lower(),
        priority=int(parts[3]),
        ip=parts[4],
        port=int(parts[5]),
        ice_type=parts[7],
    )
