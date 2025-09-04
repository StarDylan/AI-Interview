/**
 * WebSocket hook with ticket-based authentication support for the Interview Helper app.
 * 
 * This hook implements a secure two-step authentication process:
 * 1. First, it requests an authentication ticket from the backend using the user's JWT token
 * 2. Then, it uses the ticket to establish the WebSocket connection
 * 
 * This approach provides enhanced security by ensuring tickets are single-use and time-limited.
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

            // Step 1: Request an authentication ticket from the backend
            const ticketResponse = await fetch(`${backendUrl}/auth/ticket`, {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${auth.user.access_token}`,
                    "Content-Type": "application/json",
                },
            });

            if (!ticketResponse.ok) {
                throw new Error(
                    `Failed to obtain authentication ticket: ${ticketResponse.status}`,
                );
            }

            const ticketData = await ticketResponse.json();
            const ticketId = ticketData.ticket_id;

            console.log("Obtained authentication ticket:", ticketId);

            // Step 2: Create WebSocket connection with the ticket
            const ws = new WebSocket(`${wsUrl}/ws?ticket_id=${ticketId}`);

            ws.onopen = () => {
                console.log("WebSocket connected with ticket-based authentication");
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
                    setError("Authentication failed - ticket invalid or expired");
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
            const errorMessage = err instanceof Error ? err.message : "Unknown error";
            setError(`Failed to connect: ${errorMessage}`);
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
