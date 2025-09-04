import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "normalize.css";
import App from "./App.tsx";
import { AuthProvider } from "react-oidc-context";
import { OIDC_AUTHORITY, OIDC_CLIENT_ID, SITE_URL } from "./constants.ts";

const googleOidcConfig = {
    authority: OIDC_AUTHORITY,
    client_id: OIDC_CLIENT_ID,
    redirect_uri: `${SITE_URL}/auth/callback`,
    response_type: "code",
    scope: "openid profile email",
    // Google OIDC specific settings
    prompt: "select_account",
    post_logout_redirect_uri: SITE_URL,
};

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <AuthProvider {...googleOidcConfig}>
            <App />
        </AuthProvider>
    </StrictMode>,
);
