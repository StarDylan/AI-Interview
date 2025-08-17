from aiortc.rtcpeerconnection import RTCPeerConnection

from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.types import ResourceKey


# Static Resource Key Types
WEBSOCKET = ResourceKey[ConcurrentWebSocket]("websocket")
WEBRTC_PEER_CONNECTION = ResourceKey[RTCPeerConnection]("webrtc")
