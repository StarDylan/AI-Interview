import { createContext } from "react";
import { useAuthenticatedWebSocket as useAuthenticatedWebSocket } from "./useAuthenticatedWebSocket";

export const WebSocketContext = createContext<ReturnType<
    typeof useAuthenticatedWebSocket
> | null>(null);
