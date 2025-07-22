export const MessageType = {
  OFFER: "offer",
  ANSWER: "answer",
  ICE_CANDIDATE: "ice_candidate",
} as const;

interface OfferMessage {
  type: number;
  sdp: string;
}

interface AnswerMessage {
  type: typeof MessageType.ANSWER;
  sdp: string;
}

interface IceCandidateMessage {
  type: typeof MessageType.ICE_CANDIDATE;
  candidate: RTCIceCandidateInit;
}

type SignalingMessage = OfferMessage | AnswerMessage | IceCandidateMessage;

export type Message = SignalingMessage;
