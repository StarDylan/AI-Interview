import { Button, Paper } from "@mantine/core";
import { IconMicrophone } from "@tabler/icons-react";
import { createWebRTCClient } from "../lib/webrtc";
import { useCallback, useEffect, useRef, useState } from "react";
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

    // Use useRef to hold the webrtc client instance
    const webrtcClient = useRef<ReturnType<typeof createWebRTCClient> | null>(
        null,
    );

    // Use useCallback for a stable callback function
    const handleConnectionChange = useCallback(
        (state: validConnectionStates) => {
            setConnectionState(state);
        },
        [],
    );

    // Create the webrtc client only once
    useEffect(() => {
        if (!webrtcClient.current) {
            webrtcClient.current = createWebRTCClient({
                sendMessage: ws.sendMessage,
                onConnectionChange: handleConnectionChange,
            });
        }
    }, [ws.sendMessage, handleConnectionChange]);
    useEffect(() => {
        if (!webrtcClient.current) {
            return;
        }

        const types = ["offer", "ice_candidate", "answer"] as const;
        for (const type of types) {
            ws.registerMessageHandler(
                type,
                webrtcClient.current.handleWebsocketSignaling,
            );
        }

        // Return a cleanup function to unregister handlers when the component unmounts
        return () => {
            for (const type of types) {
                ws.deregisterMessageHandler(type);
            }
        };
    }, [webrtcClient.current]);

    function startSendingAudio() {
        if (webrtcClient.current) {
            webrtcClient.current.startAudioStream();
        }
    }

    function stopSendingAudio() {
        if (webrtcClient.current) {
            webrtcClient.current.stopAudioStream();
        }
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
