import { Button, Paper } from "@mantine/core";
import { useEffect, useState } from "react";
import { useWebSocket } from "../lib/useWebsocket";
import { MessageType } from "../lib/message";

export function Ping() {
    const ws = useWebSocket();
    const [pongReceived, setPongReceived] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        function handlePong() {
            setPongReceived(true);
            setLoading(false);
        }
        ws.registerMessageHandler(MessageType.PONG, handlePong);
        return () => {
            ws.deregisterMessageHandler(MessageType.PONG);
        };
    }, [ws]);

    const sendPing = () => {
        setLoading(true);
        setPongReceived(false);
        ws.sendMessage({
            type: MessageType.PING,
            timestamp: Date.now().toString(),
        });
    };

    return (
        <Paper p="md" shadow="sm">
            <Button
                onClick={sendPing}
                loading={loading}
                disabled={ws.connectionStatus != "connected"}
            >
                Send Ping
            </Button>
            {pongReceived && <div>Pong received!</div>}
            {ws.connectionStatus}
        </Paper>
    );
}
