import React from "react";

const BACKEND = import.meta.env.VITE_BACKEND_URL;

const LoginButton = () => {
    const handleLogin = () => {
        // The URL of your FastAPI backend's login endpoint
        const fastapiLoginUrl = `${BACKEND}/login`;

        // Redirect the browser to the backend login endpoint
        window.location.href = fastapiLoginUrl;
    };

    return (
        <div style={{ textAlign: "center", marginTop: "100px" }}>
            <h1>Welcome to the App!</h1>
            <p>Please log in to continue.</p>
            <button
                onClick={handleLogin}
                style={{
                    padding: "12px 24px",
                    fontSize: "16px",
                    color: "#fff",
                    backgroundColor: "#007bff",
                    border: "none",
                    borderRadius: "5px",
                    cursor: "pointer",
                    transition: "background-color 0.3s ease",
                }}
            >
                Login with your Identity Provider
            </button>
        </div>
    );
};

export default LoginButton;
