/**
 * WebSocket hook with authentication support for the Interview Helper app.
 */

import { useAuth } from "react-oidc-context";
import { useEffect, useState, useRef } from "react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WebSocketMessage = any;

interface WebSocketClientProps {
    onMessage?: (message: WebSocketMessage) => void;
    onConnectionChange?: (status: string) => void;
}

export function useAuthenticatedWebSocket({
    onMessage,
    onConnectionChange,
}: WebSocketClientProps = {}) {
    const auth = useAuth();
    const [connectionStatus, setConnectionStatus] = useState<
        "disconnected" | "connecting" | "connected"
    >("disconnected");
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    const connect = async () => {
        if (!auth.isAuthenticated || !auth.user?.access_token) {
            setError("User not authenticated");
            return;
        }

        try {
            setConnectionStatus("connecting");
            setError(null);
            onConnectionChange?.("connecting");

            // Get backend URL from environment
            const backendUrl =
                import.meta.env.VITE_BACKEND_URL || "http://localhost:3000";
            const wsUrl = backendUrl.replace("http", "ws");

            // Create WebSocket connection with authentication token
            const ws = new WebSocket(
                `${wsUrl}/ws?token=${auth.user.access_token}`,
            );

            ws.onopen = () => {
                console.log("WebSocket connected");
                setConnectionStatus("connected");
                onConnectionChange?.("connected");
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    onMessage?.(message);
                } catch (e) {
                    console.error("Failed to parse WebSocket message:", e);
                }
            };

            ws.onclose = (event) => {
                console.log(
                    "WebSocket disconnected:",
                    event.code,
                    event.reason,
                );
                setConnectionStatus("disconnected");
                onConnectionChange?.("disconnected");

                if (event.code === 1008) {
                    setError("Authentication failed");
                } else if (event.code !== 1000) {
                    setError(
                        `Connection closed: ${event.reason || "Unknown error"}`,
                    );
                }
            };

            ws.onerror = (event) => {
                console.error("WebSocket error:", event);
                setError("WebSocket connection error");
                setConnectionStatus("disconnected");
                onConnectionChange?.("disconnected");
            };

            wsRef.current = ws;
        } catch (err) {
            console.error("Failed to connect to WebSocket:", err);
            setError("Failed to connect");
            setConnectionStatus("disconnected");
            onConnectionChange?.("disconnected");
        }
    };

    const disconnect = () => {
        if (wsRef.current) {
            wsRef.current.close(1000, "User disconnected");
            wsRef.current = null;
        }
    };

    const sendMessage = (message: WebSocketMessage) => {
        if (wsRef.current && connectionStatus === "connected") {
            wsRef.current.send(JSON.stringify(message));
            return true;
        }
        return false;
    };

    // Clean up on unmount
    useEffect(() => {
        return () => {
            disconnect();
        };
    }, []);

    return {
        connectionStatus,
        error,
        connect,
        disconnect,
        sendMessage,
        isConnected: connectionStatus === "connected",
    };
}
