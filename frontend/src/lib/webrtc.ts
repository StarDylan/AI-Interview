// Configuration

import type { Message } from "./message";
import { toWebSocketUrl } from "./url-utils";

const BACKEND = import.meta.env.VITE_BACKEND_URL;

export const SIGNALING_SERVER_URL = toWebSocketUrl(BACKEND);

export const ICE_SERVERS = [
  { urls: "stun:stun.l.google.com:19302" },
  // { urls: 'turn:your.turn.server:3478', username: 'user', credential: 'pass' }
];

/** BadConfiguration error class
 *
 * This is when the user is not at fault, but the web admin did not configure
 * the server correctly.
 */
export class BadConfiguration extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BadConfiguration";
  }
}

export function createWebRTCClient({
  signalingUrl,
  iceServers,
  onConnectionChange,
}: {
  signalingUrl: string;
  iceServers: RTCIceServer[];
  onConnectionChange: (state: "connected" | "disconnected") => void;
}) {
  if (!signalingUrl) throw new Error("Invalid signaling URL");
  if (!iceServers || !Array.isArray(iceServers)) {
    throw new Error("Invalid ICE servers configuration");
  }

  let localStream: MediaStream;

  const ws = initWebSocket(handleSignal);
  const pc = new RTCPeerConnection({ iceServers });

  async function startAudioStream() {
    localStream = await setupLocalStream();
  }

  async function stopAudioStream() {
    localStream?.getTracks().forEach((track) => track.stop());
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
    const msg = JSON.parse(data);
    onSignal(msg);
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
      "WebRTC requires a secure context (HTTPS or localhost)"
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
export function sendSignal(message: Message, ws: WebSocket) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

/**
 * Create RTCPeerConnection and bind event handlers
 * @param {Object} config - ICE servers config
 * @param {Object} callbacks - { onIceCandidate, onTrack }
 */
export function initPeerConnection(config = {}, callbacks = {}) {
  pc = new RTCPeerConnection(config);
  pc.onicecandidate = ({ candidate }) => callbacks.onIceCandidate(candidate);
  pc.ontrack = (event) => callbacks.onTrack(event.streams[0]);
  return pc;
}

/**
 * Get user media (camera + mic)
 * @returns {Promise<MediaStream>}
 */
export async function getLocalStream() {
  localStream = await navigator.mediaDevices.getUserMedia({
    video: true,
    audio: true,
  });
  return localStream;
}

/**
 * Add local tracks to RTCPeerConnection
 * @param {RTCPeerConnection} peerConnection
 * @param {MediaStream} stream
 */
export function addLocalTracks(peerConnection, stream) {
  stream.getTracks().forEach((track) => peerConnection.addTrack(track, stream));
}

/**
 * Handle incoming signaling messages
 * @param {Object} message
 */
export async function handleSignal(message) {
  if (!pc) return;
  if (message.sdp) {
    await pc.setRemoteDescription(new RTCSessionDescription(message.sdp));
    if (message.sdp.type === "offer") {
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      sendSignal({ sdp: pc.localDescription });
    }
  } else if (message.candidate) {
    await pc.addIceCandidate(new RTCIceCandidate(message.candidate));
  }
}

/**
 * Create and send an offer
 */
export async function createAndSendOffer() {
  if (!pc) throw new Error("PeerConnection not initialized");
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  sendSignal({ sdp: pc.localDescription });
}

/**
 * Close connections and cleanup
 */
export function closeConnections() {
  if (pc) pc.close();
  if (ws) ws.close();
  pc = null;
  ws = null;
  localStream = null;
}

/**
 * Hook to attach event handlers (optional)
 * @param {Object} cb - { onRemoteStream(stream), onLocalStream(stream) }
 */
export async function startWebRTC(cb = {}) {
  initWebSocket(handleSignal);
  const stream = await getLocalStream();
  cb.onLocalStream?.(stream);
  const connection = initPeerConnection(
    { iceServers: ICE_SERVERS },
    {
      onIceCandidate: (candidate) => sendSignal({ candidate }),
      onTrack: (remoteStream) => cb.onRemoteStream?.(remoteStream),
    }
  );
  addLocalTracks(connection, stream);
  return connection;
}
