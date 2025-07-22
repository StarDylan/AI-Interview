import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";

function App() {

    
  return (
    <>
      <h1>WebRTC Audio Streaming</h1>

      <div className="controls">
        <button id="startBtn">Start Audio Stream</button>
        <button id="stopBtn" disabled>
          Stop Stream
        </button>
      </div>

      <div id="status" className="status">
        Ready to connect
      </div>
    </>
  );
}

export default App;
