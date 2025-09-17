export const MessageType = {
    OFFER: "offer",
    ANSWER: "answer",
    ICE_CANDIDATE: "ice_candidate",
} as const;

interface OfferMessage {
    type: typeof MessageType.OFFER;
    data: {
        sdp: RTCSessionDescriptionInit;
    };
}

interface AnswerMessage {
    type: typeof MessageType.ANSWER;
    data: {
        sdp: RTCSessionDescriptionInit;
    };
}

interface IceCandidateMessage {
    type: typeof MessageType.ICE_CANDIDATE;
    data: {
        candidate: RTCIceCandidateInit;
    };
}

export interface PingMessage {
    type: "ping" | "pong";
    timestamp: string;
}

export type SignalingMessage =
    | OfferMessage
    | AnswerMessage
    | IceCandidateMessage;

export type Message = SignalingMessage | PingMessage;

export interface Envelope {
    message: Message;
}
