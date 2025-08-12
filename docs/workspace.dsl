workspace "Thesis V2" {
    !identifiers hierarchical
    !adrs adr

    model {
        u = person "User" "A Search and Rescue interviewer"
        
        ss = softwareSystem "Interview Helper" {
            webapp = container "Web Application" \
                "Delivers the static content and the Interview Helper single page application."\
                "Vite"

            spa = container "Single Page Application"\
                "Provides all the functionality of Interview Helper including recording, live interview feedback, and review."\
                "TypeScript and React"

            !include backend.dsl
            
            db = container "Persistent Database" "Stores project data including AI comments, transcription, etc." "SQLite" {
                tags "Database"
            }
            bs = container "Blob Storage" "Stores binary blobs" "Filesystem"
     
            backend -> spa "Recieves interview feedback and any user actions" "WebSocket"
            spa -> backend "Sends Live Interview Audio" "WebRTC"
            
            backend -> db "Reads from and writes to"
            backend -> bs "Writes full audio files to"
        }
    
        uses_relation = u -> ss.spa "Uses"
        website_relation = u -> ss.webapp "Visits Interview Helper Website" "HTTPS"

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
    }
}