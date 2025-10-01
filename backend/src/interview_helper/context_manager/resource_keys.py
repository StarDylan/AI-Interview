from wave import Wave_write
from aiortc.rtcpeerconnection import RTCPeerConnection

from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.types import ResourceKey, UserId


# Static Resource Key Types
WEBSOCKET = ResourceKey[ConcurrentWebSocket]("websocket")
USER_ID = ResourceKey[UserId]("user_id")
USER_IP = ResourceKey[str]("user_ip")

WEBRTC_PEER_CONNECTION = ResourceKey[RTCPeerConnection]("webrtc")
WAVE_WRITE_FD = ResourceKey[Wave_write]("wave_fd")
