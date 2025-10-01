import { useAuthenticatedWebSocket } from "./useAuthenticatedWebSocket";
import { WebSocketContext } from "./WebSocketContext";

interface WebSocketProviderProps {
    children: React.ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
    const ws = useAuthenticatedWebSocket();
    return (
        <WebSocketContext.Provider value={ws}>
            {children}
        </WebSocketContext.Provider>
    );
}
