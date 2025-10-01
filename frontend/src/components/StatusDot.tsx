import React from "react";

export default function StatusDot({
    status,
    size = 12,
}: {
    status: "connected" | "connecting" | "disconnected";
    size?: number;
    title?: string;
}) {
    const palette =
        status === "connected"
            ? { base: "#22c55e", light: "#86efac", dark: "#16a34a" }
            : status === "disconnected"
              ? { base: "#ef4444", light: "#fca5a5", dark: "#dc2626" }
              : { base: "#facc15", light: "#fde047", dark: "#eab308" };

    const style: React.CSSProperties = {
        width: size,
        height: size,
        borderRadius: "50%",
        display: "inline-block",
        // Subtle bevel using a gradient plus inset shadows
        background: `linear-gradient(145deg, ${palette.light} 0%, ${palette.base} 60%, ${palette.dark} 100%)`,
        boxShadow:
            "inset 0 1px 2px rgba(0,0,0,0.35), inset 0 -1px 2px rgba(255,255,255,0.25), 0 0 0 1px rgba(0,0,0,0.1)",
        // Crisp edges on any background
        outline: "none",
    };

    return <span role="status" aria-label={status} style={style} />;
}
