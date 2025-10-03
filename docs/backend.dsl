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
    
    audio_processor -> analyzer "Provides transcription data to"
    audio_stream -> audio_processor "Provides audio data to"
}

backend.websocket_controller -> spa "Receives interview feedback and any user actions" "WebSocket"
spa -> backend.audio_stream "Sends Live Interview Audio" "WebRTC"
backend.websocket_controller -> backend.audio_stream "Provides WebRTC signaling for"

backend.session_context -> db "Reads from and writes to"
backend.session_context -> fs "Writes audio chunks to"


backend.session_context -> oidc "Authenticates user tokens against" "OIDC JSON over HTTPS"

spa -> oidc "Logs in via" "HTTPS"
