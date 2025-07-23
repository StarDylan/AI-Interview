export const MessageType = {
  OFFER: "offer",
  ANSWER: "answer",
  ICE_CANDIDATE: "ice_candidate",
} as const;

interface OfferMessage {
  type: typeof MessageType.OFFER;
  sdp: RTCSessionDescriptionInit;
}

interface AnswerMessage {
  type: typeof MessageType.ANSWER;
  sdp: RTCSessionDescriptionInit;
}

interface IceCandidateMessage {
  type: typeof MessageType.ICE_CANDIDATE;
  candidate: RTCIceCandidateInit;
}

export type SignalingMessage =
  | OfferMessage
  | AnswerMessage
  | IceCandidateMessage;

export type Message = SignalingMessage;
