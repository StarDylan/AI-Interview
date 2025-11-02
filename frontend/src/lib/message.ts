export const MessageType = {
    OFFER: "offer",
    ANSWER: "answer",
    ICE_CANDIDATE: "ice_candidate",
    PING: "ping",
    PONG: "pong",
    TRANSCRIPTION: "transcription",
    AI_RESULT: "ai_result",
    CATCHUP: "catchup",
    PROJECT_METADATA: "project_metadata",
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
    type: typeof MessageType.PING | typeof MessageType.PONG;
    timestamp: string;
}

export interface TranscriptionMessage {
    type: typeof MessageType.TRANSCRIPTION;
    timestamp: string;
    text: string;
}

export interface AIResultMessage {
    type: typeof MessageType.AI_RESULT;
    timestamp: string;
    text: string;
}

export interface CatchupMessage {
    type: typeof MessageType.CATCHUP;
    timestamp: string;
    transcript: string;
    insights: string[];
}

export interface ProjectMetadataMessage {
    type: typeof MessageType.PROJECT_METADATA;
    timestamp: string;
    project_id: string;
    project_name: string;
}

export type SignalingMessage =
    | OfferMessage
    | AnswerMessage
    | IceCandidateMessage;

export type Message =
    | SignalingMessage
    | PingMessage
    | TranscriptionMessage
    | AIResultMessage
    | CatchupMessage
    | ProjectMetadataMessage;

export interface Envelope {
    message: Message;
}
