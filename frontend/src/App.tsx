import "@mantine/core/styles.css";

import { MantineProvider } from "@mantine/core";
import { useAuth } from "react-oidc-context";
import {
    BrowserRouter as Router,
    Routes,
    Route,
    useLocation,
} from "react-router-dom";
import AppLayout from "./AppLayout";
import AuthCallback from "./AuthCallback";

function AppContent() {
    const auth = useAuth();
    const location = useLocation();

    // Handle callback route
    if (location.pathname === "/auth/callback") {
        return <AuthCallback />;
    }

    // Handle loading state
    if (auth.isLoading) {
        return (
            <div
                style={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    height: "100vh",
                }}
            >
                Loading...
            </div>
        );
    }

    // Handle authentication errors
    if (auth.error) {
        return (
            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    alignItems: "center",
                    height: "100vh",
                    gap: "1rem",
                }}
            >
                <h2>Authentication Error</h2>
                <p>Error: {auth.error.message}</p>
                <button
                    onClick={() => auth.signinRedirect()}
                    style={{
                        padding: "12px 24px",
                        fontSize: "16px",
                        color: "#fff",
                        backgroundColor: "#007bff",
                        border: "none",
                        borderRadius: "5px",
                        cursor: "pointer",
                    }}
                >
                    Try Again
                </button>
            </div>
        );
    }

    // If user is authenticated, show the main app
    if (auth.isAuthenticated) {
        return (
            <AppLayout user={auth.user} onSignOut={() => auth.removeUser()} />
        );
    }

    // If not authenticated, show login page
    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                height: "100vh",
                gap: "1rem",
            }}
        >
            <h1>Welcome to Interview Helper</h1>
            <p>Please sign in with your Google account to continue.</p>
            <button
                onClick={() => auth.signinRedirect()}
                style={{
                    padding: "12px 24px",
                    fontSize: "16px",
                    color: "#fff",
                    backgroundColor: "#4285f4",
                    border: "none",
                    borderRadius: "5px",
                    cursor: "pointer",
                    transition: "background-color 0.3s ease",
                }}
                onMouseEnter={(e) =>
                    (e.currentTarget.style.backgroundColor = "#357ae8")
                }
                onMouseLeave={(e) =>
                    (e.currentTarget.style.backgroundColor = "#4285f4")
                }
            >
                Sign in with Google
            </button>
        </div>
    );
}

function App() {
    return (
        <MantineProvider>
            <Router>
                <Routes>
                    <Route path="/*" element={<AppContent />} />
                </Routes>
            </Router>
        </MantineProvider>
    );
}

export default App;
