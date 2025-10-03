import { Button, Center, Group, Loader, Paper, Text } from "@mantine/core";
import { IconMicrophone } from "@tabler/icons-react";
import { createWebRTCClient } from "../lib/webrtc";
import { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket } from "../lib/useWebsocket";
import { MessageType, type TranscriptionMessage } from "../lib/message";

export function AudioSender() {
    type validConnectionStates =
        | "disconnected"
        | "connected"
        | "connecting"
        | "failed";
    const [connectionState, setConnectionState] =
        useState<validConnectionStates>("disconnected");

    const [transcript, setTranscript] = useState("");

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

        const types = [
            MessageType.OFFER,
            MessageType.ICE_CANDIDATE,
            MessageType.ANSWER,
        ] as const;
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
            ws.deregisterMessageHandler("transcription");
        };
    }, [webrtcClient.current]);

    useEffect(() => {
        ws.registerMessageHandler(
            "transcription",
            (message: TranscriptionMessage) => {
                setTranscript(
                    (prevState: string) => prevState + " " + message.text,
                );
            },
        );
        return () => {
            ws.deregisterMessageHandler("transcription");
        };
    });

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

    const isConnected = connectionState === "connected";
    const isConnecting = connectionState === "connecting";
    const buttonText = isConnected ? "Stop Recording" : "Start Recording";
    const buttonColor = isConnected ? "red" : "green";
    const buttonVariant = isConnected ? "filled" : "light";
    const statusText = isConnected
        ? "Recording..."
        : isConnecting
          ? "Connecting..."
          : "Ready to Start";
    const statusColor = isConnected ? "red" : isConnecting ? "yellow" : "gray";

    return (
        <Group align="stretch" p="lg" maw={500} mx="auto">
            {/* Audio Control Button */}
            <Paper shadow="md" radius="lg" p="xl" withBorder>
                <Center>
                    <Button
                        variant={buttonVariant}
                        color={buttonColor}
                        leftSection={
                            isConnecting ? (
                                <Loader size="sm" color="white" />
                            ) : (
                                <IconMicrophone size={18} />
                            )
                        }
                        size="xl"
                        radius="xl"
                        loading={isConnecting}
                        disabled={
                            ws.connectionStatus !== "connected" && !isConnecting
                        }
                        onClick={() => {
                            if (connectionState === "disconnected") {
                                startSendingAudio();
                            } else if (connectionState === "connected") {
                                stopSendingAudio();
                            }
                        }}
                        style={{ minWidth: 200 }} // Ensure consistent button size
                    >
                        {buttonText}
                    </Button>
                </Center>
                <Text ta="center" mt="md" size="sm" c={statusColor} fw={500}>
                    {statusText}
                </Text>
            </Paper>

            {/* Transcript Display */}
            <Paper shadow="sm" radius="md" p="lg" withBorder>
                <Text size="lg" fw={600} mb="xs">
                    Transcript
                </Text>
                <Text style={{ whiteSpace: "pre-wrap" }} c="dimmed">
                    {transcript}
                </Text>
            </Paper>
        </Group>
    );
}
