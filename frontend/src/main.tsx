import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "normalize.css";
import App from "./App.tsx";
import { AuthProvider } from "react-oidc-context";
import { OIDC_AUTHORITY, OIDC_CLIENT_ID, SITE_URL } from "./constants.ts";
import { WebSocketProvider } from "./lib/WebSocketProvider.tsx";

const oidc_config = {
    authority: OIDC_AUTHORITY,
    client_id: OIDC_CLIENT_ID,
    redirect_uri: `${SITE_URL}/auth/callback`,
    response_type: "code",
    scope: "openid profile email",
};

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <AuthProvider {...oidc_config}>
            <WebSocketProvider>
                <App />
            </WebSocketProvider>
        </AuthProvider>
    </StrictMode>,
);
