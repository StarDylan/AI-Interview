from typing import Optional, Literal
from pydantic import BaseModel


class SDPData(BaseModel):
    """SDP (Session Description Protocol) data"""

    sdp: str
    type: Literal["offer", "answer"]


class ICECandidateData(BaseModel):
    """ICE candidate data"""

    candidate: str
    sdpMid: Optional[str] = None
    sdpMLineIndex: Optional[int] = None


class OfferMessage(BaseModel):
    """WebRTC offer message"""

    type: Literal["offer"] = "offer"
    sdp: SDPData


class AnswerMessage(BaseModel):
    """WebRTC answer message"""

    type: Literal["answer"] = "answer"
    sdp: SDPData


class ICECandidateMessage(BaseModel):
    """WebRTC ICE candidate message"""

    type: Literal["ice_candidate"] = "ice_candidate"
    candidate: ICECandidateData
