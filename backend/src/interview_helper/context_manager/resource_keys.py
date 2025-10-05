from vosk import KaldiRecognizer
from wave import Wave_write
from aiortc.rtcpeerconnection import RTCPeerConnection

from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.types import ResourceKey


# Static Resource Key Types
WEBSOCKET = ResourceKey[ConcurrentWebSocket]("websocket")

WEBRTC_PEER_CONNECTION = ResourceKey[RTCPeerConnection]("webrtc")
WAVE_WRITE_FD = ResourceKey[Wave_write]("wave_fd")
TRANSCRIBER_SESSION = ResourceKey[KaldiRecognizer]("kalidi_transcriber")
