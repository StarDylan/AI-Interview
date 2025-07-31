import { useMemo, useState } from "react";
import "./App.css";
import { createWebRTCClient } from "./lib/webrtc";

function App() {
  const [connectionState, setConnectionState] = useState("disconnected");

  const webRTCClient = useMemo(
    () =>
      createWebRTCClient({
        onConnectionChange: setConnectionState,
      }),
    []
  );

  return (
    <div className="font-sans max-w-2xl mx-auto p-5">
      <h1 className="text-3xl font-bold mb-6">WebRTC Audio Streaming</h1>

      <div className="my-5">
        <button
          onClick={webRTCClient.startAudioStream}
          className="px-5 py-2 m-1 text-lg cursor-pointer rounded bg-blue-600 text-white hover:bg-blue-700 transition"
        >
          Start Audio Stream
        </button>
        <button
          className="px-5 py-2 m-1 text-lg cursor-pointer rounded bg-gray-400 text-white"
          onClick={() => {
            console.log("Stopping audio stream");
            webRTCClient.stopAudioStream();
          }}
        >
          Stop Stream
        </button>
      </div>

      <div
        id="status"
        className={`status p-2 my-2 rounded 
        ${status === "Connected to audio stream" ? "bg-green-100" : ""}
        ${status === "Failed to connect to audio stream" ? "bg-red-100" : ""}
        ${
          status !== "Connected to audio stream" &&
          status !== "Failed to connect to audio stream"
            ? "bg-gray-100"
            : ""
        }
      `}
      >
        {connectionState}
      </div>
    </div>
  );
}

export default App;
