class WebRTCAudioClient {
  constructor() {
    this.ws = null;
    this.pc = null;
    this.localStream = null;
    this.isConnected = false;

    this.startBtn = document.getElementById("startBtn");
    this.stopBtn = document.getElementById("stopBtn");
    this.status = document.getElementById("status");

    this.setupEventListeners();
  }

  setupEventListeners() {
    this.startBtn.addEventListener("click", () => this.start());
    this.stopBtn.addEventListener("click", () => this.stop());
  }

  updateStatus(message, type = "info") {
    this.status.textContent = message;
    this.status.className = `status ${type}`;
    console.log(message);
  }

  async start() {
    try {
      this.updateStatus("Requesting microphone access...");

      // Get user media (audio only)
      this.localStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      this.updateStatus("Microphone access granted. Connecting to server...");

      // Connect to WebSocket signaling server
      await this.connectWebSocket();

      // Create peer connection
      this.createPeerConnection();

      // Add local stream to peer connection
      this.localStream.getTracks().forEach((track) => {
        this.pc.addTrack(track, this.localStream);
      });

      // Create and send offer
      await this.createOffer();

      this.startBtn.disabled = true;
      this.stopBtn.disabled = false;
    } catch (error) {
      this.updateStatus(`Error: ${error.message}`, "error");
      console.error("Start error:", error);
    }
  }

  async connectWebSocket() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket("ws://localhost:8765");

      this.ws.onopen = () => {
        this.updateStatus("Connected to signaling server");
        resolve();
      };

      this.ws.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        await this.handleSignalingMessage(message);
      };

      this.ws.onerror = (error) => {
        this.updateStatus("WebSocket error", "error");
        reject(error);
      };

      this.ws.onclose = () => {
        this.updateStatus("Disconnected from server");
        this.isConnected = false;
      };
    });
  }

  createPeerConnection() {
    const config = {
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    };

    this.pc = new RTCPeerConnection(config);

    this.pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.sendSignalingMessage({
          type: "ice-candidate",
          candidate: event.candidate,
        });
      }
    };

    this.pc.onconnectionstatechange = () => {
      this.updateStatus(`Connection state: ${this.pc.connectionState}`);
      if (this.pc.connectionState === "connected") {
        this.isConnected = true;
        this.updateStatus("Audio streaming active", "connected");
      }
    };
  }

  async createOffer() {
    const offer = await this.pc.createOffer();
    await this.pc.setLocalDescription(offer);

    this.sendSignalingMessage({
      type: "offer",
      sdp: offer,
    });
  }

  async handleSignalingMessage(message) {
    switch (message.type) {
      case "answer":
        await this.pc.setRemoteDescription(
          new RTCSessionDescription(message.sdp)
        );
        break;

      case "ice-candidate":
        await this.pc.addIceCandidate(new RTCIceCandidate(message.candidate));
        break;

      default:
        console.log("Unknown message type:", message.type);
    }
  }

  sendSignalingMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  stop() {
    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => track.stop());
      this.localStream = null;
    }

    if (this.pc) {
      this.pc.close();
      this.pc = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.startBtn.disabled = false;
    this.stopBtn.disabled = true;
    this.isConnected = false;

    this.updateStatus("Stopped");
  }
}

// Initialize the client when page loads
document.addEventListener("DOMContentLoaded", () => {
  new WebRTCAudioClient();
});
