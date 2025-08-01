/**
 * Converts an HTTP(S) backend URL to a WS(S) WebSocket URL.
 * Falls back to wss:// if no protocol is specified.
 *
 * @param {string} backendUrl - The backend URL (from env or otherwise)
 * @returns {string} - The WebSocket-compatible URL
 * @throws {Error} - If input is invalid or empty
 */
export function toWebSocketUrl(backendUrl: string): string {
  if (!backendUrl || typeof backendUrl !== "string") {
    throw new Error("Invalid backend URL provided: " + backendUrl);
  }

  try {
    // Add default protocol if missing
    const hasProtocol = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//.test(backendUrl);

    if (!hasProtocol) {
      throw new Error(
        "Backend URL must include a protocol (http:// or https://)",
      );
    }

    const url = new URL(backendUrl);

    // Convert protocol to ws or wss
    url.protocol =
      url.protocol === "http:"
        ? "ws:"
        : url.protocol === "https:"
          ? "wss:"
          : url.protocol;

    return url.toString();
  } catch (err: unknown) {
    throw new Error(
      `Failed to parse backend URL: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  }
}
