import { Button, Paper } from "@mantine/core";
import { IconMicrophone } from "@tabler/icons-react";
import { createWebRTCClient } from "../lib/webrtc";
import { useState } from "react";
import { useWebSocket } from "../lib/useWebsocket";

export function AudioSender() {
    type validConnectionStates =
        | "disconnected"
        | "connected"
        | "connecting"
        | "failed";
    const [connectionState, setConnectionState] =
        useState<validConnectionStates>("disconnected");

    const ws = useWebSocket();

    const webrtc = createWebRTCClient({
        sendMessage: ws.sendMessage,
        onConnectionChange: setConnectionState,
    });

    for (const type of ["offer", "ice_candidate", "answer"] as const) {
        ws.registerMessageHandler(type, webrtc.handleWebsocketSignaling);
    }

    function startSendingAudio() {
        webrtc.startAudioStream();
    }

    function stopSendingAudio() {
        webrtc.stopAudioStream();
    }

    return (
        <Paper>
            <Button
                variant={connectionState === "connected" ? "filled" : "outline"}
                color={connectionState === "connected" ? "red" : undefined}
                leftSection={<IconMicrophone size={16} />}
                size="md"
                radius="lg"
                loading={connectionState === "connecting"}
                onClick={() => {
                    if (connectionState === "disconnected") {
                        startSendingAudio();
                    } else if (connectionState === "connected") {
                        stopSendingAudio();
                    }
                }}
            >
                {connectionState === "disconnected" && "Start Audio"}
                {connectionState === "connected" && "Stop Audio"}
            </Button>
        </Paper>
    );
}
