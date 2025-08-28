// Configuration

import type { Envelope, Message, SignalingMessage } from "./message";
import { toWebSocketUrl } from "./url-utils";

const BACKEND = import.meta.env.VITE_BACKEND_URL + "/ws";

export const SIGNALING_SERVER_URL = toWebSocketUrl(BACKEND);

export const ICE_SERVERS = [
    { urls: "stun:stun.l.google.com:19302" },
    // { urls: 'turn:your.turn.server:3478', username: 'user', credential: 'pass' }
];

/**
 * BadConfiguration error
 *
 * This is when the web admin did not configure
 * the server correctly.
 */
export class BadConfiguration extends Error {
    constructor(message: string) {
        super(message);
        this.name = "BadConfiguration";
    }
}

export function createWebRTCClient({
    onConnectionChange,
}: {
    onConnectionChange: (
        state: "ready" | "connected" | "disconnected" | "failed" | "connecting",
    ) => void;
}) {
    if (!SIGNALING_SERVER_URL) throw new Error("Invalid signaling URL");

    onConnectionChange("disconnected");

    let localStream: MediaStream, pc: RTCPeerConnection;

    async function handleWebsocketSignaling(msg: SignalingMessage) {
        if (msg.type === "answer") {
            await pc.setRemoteDescription(
                new RTCSessionDescription(msg.data.sdp),
            );
        } else if (msg.type === "ice_candidate") {
            await pc.addIceCandidate(new RTCIceCandidate(msg.data.candidate));
        }
    }

    // TODO: handle websocket over entire website.
    let ws: WebSocket | null = initWebSocket(handleWebsocketSignaling);

    ws.onopen = () => {
        console.log("WebSocket connection established");
        onConnectionChange("ready");
    };

    ws.onclose = (evt) => {
        if (evt.code == 3001) {
            console.log("ws closed");
            ws = null;
        } else {
            ws = null;
            console.warn("ws connection error");
            console.warn(evt);
        }
        console.log("WebSocket connection closed");
        onConnectionChange("disconnected");
    };

    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        onConnectionChange("failed");
    };

    async function startAudioStream() {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            throw new Error("WebSocket connection not established");
        }

        onConnectionChange("connecting");
        console.log("Starting audio stream...");
        pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });

        pc.onicecandidate = (event) => {
            if (event.candidate && ws) {
                console.log("Sending ICE candidate:", event.candidate);
                sendMessage(
                    {
                        type: "ice_candidate",
                        data: {
                            candidate: event.candidate,
                        },
                    },
                    ws,
                );
            }
        };

        pc.onconnectionstatechange = () => {
            if (pc.connectionState === "connected") {
                onConnectionChange("connected");
            } else if (pc.connectionState === "disconnected") {
                // If disconnected, check if we should notify the user
                onConnectionChange("disconnected");
            }
            if (pc.connectionState === "failed") {
                onConnectionChange("failed");
            }
        };

        localStream = await setupLocalStream();

        // Add local stream to peer
        console.log("Adding local stream to peer connection");
        localStream.getTracks().forEach((track) => {
            pc.addTrack(track, localStream);
        });

        console.log("Creating offer...");
        if (!ws) {
            throw new Error("WebSocket connection not established");
        }
        await createAndSendOffer(pc, ws);
        console.log("Offer sent, waiting for answer...");
    }

    async function stopAudioStream() {
        onConnectionChange("disconnected");
        localStream?.getTracks().forEach((track) => track.stop());

        // Close out all the connections
        if (pc) {
            pc.close();
        }
    }

    return { startAudioStream, stopAudioStream };
}

/**
 * Initialize WebSocket connection and setup message handler
 * @param onSignal - callback to handle incoming signaling data
 *
 * @returns the WebSocket instance
 */
export function initWebSocket(onSignal: (msg: Message) => void) {
    const ws = new WebSocket(SIGNALING_SERVER_URL);
    ws.onmessage = ({ data }) => {
        const msg = JSON.parse(data) as Envelope;
        onSignal(msg.message);
    };

    return ws;
}

/**
 * Setup local audio stream in preparation for WebRTC
 *
 * Requires a secure context (HTTPS or localhost)
 *
 * @returns Local audio stream
 */
async function setupLocalStream() {
    if (window.isSecureContext === false) {
        throw new BadConfiguration(
            "WebRTC requires a secure context (HTTPS or localhost)",
        );
    }

    // Stream just the audio
    return await navigator.mediaDevices.getUserMedia({
        audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
        },
        video: false,
    });
}
/**
 * Send signaling data over WebSocket
 * @param {Object} message - { sdp } or { candidate }
 */
export function sendMessage(message: Message, ws: WebSocket) {
    const envelope: Envelope = { message };
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(envelope));
    }
}
/**
 * Create and send an offer
 */
export async function createAndSendOffer(pc: RTCPeerConnection, ws: WebSocket) {
    if (!pc) throw new Error("PeerConnection not initialized");
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    sendMessage(
        {
            type: "offer",
            data: {
                sdp: pc.localDescription as RTCSessionDescriptionInit,
            },
        },
        ws,
    );
}
