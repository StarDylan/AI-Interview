backend = container "Backend" "Provides Interview Helper functionality." "Python" {
    audio_stream = component "Audio Stream Handler" {
        description "Handles real-time audio streaming"
    }

    session_context = component "Session Context Controller" {
        description "Stores and exposes all project/session context"
    }

    audio_processor = component "Audio Processor" {
        description "Transcribes audio and performs any additional signal processing or enrichment tasks."
    }

    analyzer = component "AI Analyzer" {
        description "Interpets the transcript with the project context to provide real-time feedback"
    }

    websocket_controller = component "WebSocket Controller" {
        description "Manages active WebSocket connections and basic user queries."
    }
    
    audio_stream -> session_context "Sends audio data to"
    audio_stream -> audio_processor "Sends audio data to"
    audio_processor -> session_context "Sends extracted audio data (e.g., transcript) to "
    analyzer -> session_context "Fetches session context during analysis from"
    analyzer -> websocket_controller "Provides feedback for users to"
    websocket_controller -> session_context "Fetches basic information from"
}

backend.websocket_controller -> spa "Receives interview feedback and any user actions" "WebSocket"
spa -> backend.audio_stream "Sends Live Interview Audio" "WebRTC"
backend.websocket_controller -> backend.audio_stream "Provides WebRTC signaling for"

backend.session_context -> db "Reads from and writes to"
backend.session_context -> fs "Writes audio chunks to"


backend.session_context -> oidc "Authenticates user tokens against" "OIDC JSON over HTTPS"

spa -> oidc "Logs in via" "HTTPS"
