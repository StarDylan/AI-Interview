import { useAuthenticatedWebSocket } from "./useAuthenticatedWebSocket";
import { WebSocketContext } from "./WebSocketContext";

interface WebSocketProviderProps {
    children: React.ReactNode;
    projectId?: string;
}

export function WebSocketProvider({
    children,
    projectId,
}: WebSocketProviderProps) {
    const ws = useAuthenticatedWebSocket(projectId);
    return (
        <WebSocketContext.Provider value={ws}>
            {children}
        </WebSocketContext.Provider>
    );
}
