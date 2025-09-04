/**
 * WebSocket demo component for the Interview Helper app.
 */

import { useState } from "react";
import { useAuthenticatedWebSocket, type WebSocketMessage } from "./useAuthenticatedWebSocket";

// Example component showing how to use the authenticated WebSocket
export function WebSocketDemo() {
    const [messages, setMessages] = useState<WebSocketMessage[]>([]);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');

    const { connect, disconnect, sendMessage, error, isConnected } = useAuthenticatedWebSocket({
        onMessage: (message) => {
            setMessages(prev => [...prev, message]);
        },
        onConnectionChange: setConnectionStatus
    });

    const handleTestMessage = () => {
        const testMessage = {
            type: 'test',
            data: 'Hello from authenticated client',
            timestamp: new Date().toISOString()
        };
        
        if (sendMessage(testMessage)) {
            console.log('Test message sent');
        } else {
            console.log('Failed to send message - not connected');
        }
    };

    return (
        <div style={{ padding: '1rem', border: '1px solid #ccc', margin: '1rem 0' }}>
            <h3>WebSocket Connection Demo</h3>
            <p>Status: <strong>{connectionStatus}</strong></p>
            {error && <p style={{ color: 'red' }}>Error: {error}</p>}
            
            <div style={{ marginBottom: '1rem' }}>
                <button 
                    onClick={connect} 
                    disabled={isConnected}
                    style={{ marginRight: '0.5rem' }}
                >
                    Connect
                </button>
                <button 
                    onClick={disconnect} 
                    disabled={!isConnected}
                    style={{ marginRight: '0.5rem' }}
                >
                    Disconnect
                </button>
                <button 
                    onClick={handleTestMessage} 
                    disabled={!isConnected}
                >
                    Send Test Message
                </button>
            </div>

            <div>
                <h4>Messages:</h4>
                <div style={{ maxHeight: '200px', overflow: 'auto', border: '1px solid #eee', padding: '0.5rem' }}>
                    {messages.length === 0 ? (
                        <p>No messages received</p>
                    ) : (
                        messages.map((msg, index) => (
                            <div key={index} style={{ marginBottom: '0.5rem', fontSize: '0.9em' }}>
                                <pre>{JSON.stringify(msg, null, 2)}</pre>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}