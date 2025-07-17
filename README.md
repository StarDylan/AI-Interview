# WebRTC Audio Streaming

A real-time audio streaming system using WebRTC with a browser client and Python server.

## Features

- Browser-based audio capture using getUserMedia()
- WebRTC peer-to-peer connection for audio streaming
- WebSocket signaling for SDP exchange and ICE candidates
- Python server using aiortc for WebRTC handling
- Real-time audio frame processing with numpy arrays

## Setup

### 1. Install uv (if not already installed)

```bash
# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

### 2. Install Python Dependencies

```bash
# Initialize project and add dependencies
uv init --no-readme
uv add aiortc websockets numpy
```

Or if you prefer to use the requirements file:

```bash
uv pip install -r requirements.txt
```

### 3. Start the Python Server

```bash
uv run server.py
```

The server will start on `ws://localhost:8765`

### 4. Open the Browser Client

Open `index.html` in your web browser or serve it via a local HTTP server:

```bash
# Using Python's built-in server
python -m http.server 8000
```

Then navigate to `http://localhost:8000`

## Usage

1. Click "Start Audio Stream" to begin capturing audio
2. Grant microphone permissions when prompted
3. The client will connect to the server and establish a WebRTC connection
4. Audio frames will be streamed to the Python server for processing

## Architecture

### Browser Client (`client.js`)

- Captures audio using `getUserMedia()`
- Creates RTCPeerConnection for WebRTC
- Handles WebSocket signaling for SDP offers/answers and ICE candidates
- Manages connection state and UI updates

### Python Server (`server.py`)

- Uses `aiortc` for WebRTC peer connection handling
- WebSocket server for signaling protocol
- Processes incoming audio frames as numpy arrays
- Extensible audio processing pipeline

## Audio Processing

The server receives audio frames that can be processed for:

- Speech recognition
- Audio analysis and visualization
- Real-time audio effects
- Recording and storage
- Machine learning inference

Modify the `AudioProcessor.process_frame()` method to add your custom audio processing logic.

## Configuration

### Audio Settings

The client requests audio with:

- Echo cancellation enabled
- Noise suppression enabled
- Auto gain control enabled

### WebRTC Configuration

- Uses Google's STUN server for NAT traversal
- Supports ICE candidate exchange for connectivity

## Troubleshooting

- Ensure microphone permissions are granted
- Check that the Python server is running on port 8765
- Verify WebSocket connection in browser developer tools
- Check server logs for WebRTC connection status
