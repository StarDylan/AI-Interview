workspace "Thesis V2" {
    !identifiers hierarchical
    !adrs adr

    model {
        u = person "User" "Search and Rescue Scribe"

        oidc = softwareSystem "OIDC Provider" {
            description "Manages user authentication"
        }

        ai = softwareSystem "LLM Service" {
            description "Processes LLM prompts and returns the result"
        }

        azure_stt = softwareSystem "STT Service" {
            description "Converts speech to text"
        }

        ss = softwareSystem "AI Interview Helper" {
            spa = container "Frontend" {
                description "Provides all the functionality of Interview Helper including recording, \
                    live interview feedback, and review."
                technology "TypeScript and React"
            }
            
            
            db = container "Database" {
                description "Stores project data including AI comments, transcription, etc." 
                technology "SQLite"
                tags "Database"
            }

            fs = container "File System" {
                tags "Filesystem"
            }
            
            !include backend.dsl
        }
    
        uses_relation = u -> ss.spa "Records interview audio"

        recieves_transcript_and_feedback = ss.spa -> u "Dsiplays transcript and suggested questions"

        ss.backend.analyzer -> ai "Sends question generation queries to"
        ss.backend.audio_processor -> azure_stt "Converts speech to text using"

        
        ss.spa -> oidc "Logs in via"
        ss.backend.session_context -> oidc "Authenticates user tokens against"

    }

    views {
        systemContext ss "Context" {
            include *
            autolayout lr
        }

        container ss "Container" {
            include *

            
        }

        component ss.backend "Backend" {
            include *
            autolayout lr
            description "All components use Python"
        }
    }
}