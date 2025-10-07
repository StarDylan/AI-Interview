import {
    Affix,
    Badge,
    Box,
    Button,
    Center,
    Divider,
    Group,
    Loader,
    Paper,
    ScrollArea,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import {
    IconAlertTriangle,
    IconBulb,
    IconMicrophone,
} from "@tabler/icons-react";
import { createWebRTCClient } from "../lib/webrtc";
import { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket } from "../lib/useWebsocket";
import {
    MessageType,
    type AIResultMessage,
    type TranscriptionMessage,
} from "../lib/message";

// Optional: a tiny Insights panel component so we keep the page clean
function InsightsPanel({ insights }: { insights: string[] }) {
    return (
        <Paper shadow="md" radius="lg" p="md" withBorder>
            <Group gap="xs" align="center">
                <IconBulb size={18} />
                <Title order={5}>Insights</Title>
            </Group>
            <Divider my="sm" />
            <Stack gap="xs">
                {insights.length === 0 ? (
                    <Text c="dimmed" size="sm">
                        No insights yet — they’ll show up here in real time.
                    </Text>
                ) : (
                    insights.map((tip, i) => (
                        <Group key={i} gap="xs">
                            <IconAlertTriangle size={14} />
                            <Text size="sm">{tip}</Text>
                        </Group>
                    ))
                )}
            </Stack>
        </Paper>
    );
}

export function AudioSender() {
    type validConnectionStates =
        | "disconnected"
        | "connected"
        | "connecting"
        | "failed";

    const isMobile = useMediaQuery("(max-width: 48em)"); // Mantine md breakpoint ~768px

    const [connectionState, setConnectionState] =
        useState<validConnectionStates>("disconnected");

    const [transcript, setTranscript] = useState("");

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [insights, setInsights] = useState<string[]>([]);

    const ws = useWebSocket();

    // Hold the webrtc client instance
    const webrtcClient = useRef<ReturnType<typeof createWebRTCClient> | null>(
        null,
    );

    // Scroll to bottom when transcript changes
    const viewportRef = useRef<HTMLDivElement | null>(null);
    useEffect(() => {
        const el = viewportRef.current;
        if (el) {
            el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
        }
    }, [transcript]);

    // Stable connection state handler
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

    // Register WS signaling handlers
    useEffect(() => {
        if (!webrtcClient.current) return;

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

        return () => {
            for (const type of types) {
                ws.deregisterMessageHandler(type);
            }
        };
    }, [ws]);

    // Register transcript handler
    useEffect(() => {
        const handleTranscription = (message: TranscriptionMessage) => {
            setTranscript(
                (prevState: string) =>
                    (prevState ? prevState + " " : "") + message.text,
            );
        };

        ws.registerMessageHandler("transcription", handleTranscription);

        return () => {
            ws.deregisterMessageHandler("transcription");
        };
    }, [ws]);

    // Register Insight Message
    useEffect(() => {
        const handleAIResults = (message: AIResultMessage) => {
            setInsights((prevState: string[]) =>
                prevState.concat([message.text]),
            );
        };

        ws.registerMessageHandler("ai_result", handleAIResults);

        return () => {
            ws.deregisterMessageHandler("ai_result");
        };
    }, [ws]);

    // (Optional) Example: if later you emit insight messages from the server,
    // register a handler here. For now, this just shows how to wire it up.
    // useEffect(() => {
    //   ws.registerMessageHandler("insight", (m: { text: string }) => {
    //     setInsights((prev) => [m.text, ...prev].slice(0, 20));
    //   });
    //   return () => ws.deregisterMessageHandler("insight");
    // }, [ws]);

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
        <Box
            // Full-bleed page container
            style={{
                height: "100dvh",
                width: "100%",
                display: "flex",
                flexDirection: isMobile ? "column" : "row",
                gap: "var(--mantine-spacing-md)",
                padding: "var(--mantine-spacing-md)",
                boxSizing: "border-box",
            }}
        >
            {/* Mobile: Insights at the top; Desktop: at the right */}
            {isMobile && (
                <Box style={{ flex: "0 0 auto" }}>
                    <InsightsPanel insights={insights} />
                </Box>
            )}

            {/* Transcript area fills the rest */}
            <Box
                style={{
                    position: "relative",
                    flex: 1,
                    minWidth: 0,
                    overflow: "hidden",
                }}
            >
                <Paper
                    withBorder
                    shadow="sm"
                    radius="lg"
                    style={{ height: "100%" }}
                >
                    <Stack gap="xs" style={{ height: "100%" }}>
                        <Group justify="space-between" p="md" pb={0}>
                            <Group gap="xs">
                                <Title order={4}>Transcript</Title>
                                {isConnected && <Badge color="red">Live</Badge>}
                            </Group>
                            <Text size="sm" c={statusColor}>
                                {statusText}
                            </Text>
                        </Group>

                        <ScrollArea
                            type="always"
                            style={{ flex: 1 }}
                            viewportRef={viewportRef}
                            offsetScrollbars
                        >
                            <Box p="md" pt={0}>
                                {transcript ? (
                                    <Text
                                        style={{
                                            whiteSpace: "pre-wrap",
                                            lineHeight: 1.6,
                                        }}
                                    >
                                        {transcript}
                                    </Text>
                                ) : (
                                    <Text c="dimmed" ta="center" py="xl">
                                        Your transcript will appear here.
                                    </Text>
                                )}
                            </Box>
                        </ScrollArea>
                    </Stack>
                </Paper>

                {/* Bottom-center recording control (floating) */}
                <Affix position={{ bottom: 24, left: 0, right: 0 }}>
                    <Center>
                        <Paper shadow="xl" radius="xl" p="sm" withBorder>
                            <Group gap="md" align="center">
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
                                    size={isMobile ? "lg" : "xl"}
                                    radius="xl"
                                    loading={isConnecting}
                                    disabled={
                                        ws.connectionStatus !== "connected" &&
                                        !isConnecting
                                    }
                                    onClick={() => {
                                        if (
                                            connectionState === "disconnected"
                                        ) {
                                            startSendingAudio();
                                        } else if (
                                            connectionState === "connected"
                                        ) {
                                            stopSendingAudio();
                                        }
                                    }}
                                    style={{ minWidth: isMobile ? 200 : 260 }}
                                >
                                    {buttonText}
                                </Button>
                            </Group>
                        </Paper>
                    </Center>
                </Affix>
            </Box>

            {!isMobile && (
                <Box style={{ flex: "0 0 340px" }}>
                    <InsightsPanel insights={insights} />
                </Box>
            )}
        </Box>
    );
}
