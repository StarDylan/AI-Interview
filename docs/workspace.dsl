workspace "Thesis V2" {
    !identifiers hierarchical
    !adrs adr

    model {
        u = person "User" "A Search and Rescue interviewer"

        ai = softwareSystem "LLM Inference Service" {
            description "Processes LLM prompts and returns the result"
        }

        ss = softwareSystem "Interview Helper" {
            webapp = container "Web Application" {
               description "Delivers the static content and the Interview Helper single page application."
               technology "Vite"
            }

            spa = container "Single Page Application" {
                description "Provides all the functionality of Interview Helper including recording, \
                    live interview feedback, and review."
                technology "TypeScript and React"
            }

            
            oidc = container "OIDC Provider" {
                description "Manages user credentials"
            }
            
            
            db = container "Persistent Database" {
                description "Stores project data including AI comments, transcription, etc." 
                technology "SQLite"
                tags "Database"
            }

            fs = container "File System" {
                tags "Filesystem"
            }

            whisper = container "Whisper Transcriber" {
                description "Transcribes audio using the SOTA Whisper model"
            }
            
            !include backend.dsl
        }
    
        uses_relation = u -> ss.spa "Uses"
        website_relation = u -> ss.webapp "Visits Interview Helper using" "HTTPS"

        ss.backend.analyzer -> ai "Sends queries to" "OpenAI Compliant API"
        ss.backend.audio_processor -> ss.whisper "Sends audio to" "Websocket"
    }

    views {
        systemContext ss "Context" {
            include *
            autolayout lr
        }

        container ss "Container" {
            include *

            
            autolayout lr
        }

        component ss.backend "Backend" {
            include *
            autolayout lr
            description "All components use Python"
        }
    }
}