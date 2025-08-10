workspace {
    !identifiers hierarchical

    model {
        u = person "User"
        ss = softwareSystem "Interview Helper" {
            wa = container "Web Application"
            db = container "Persistent Database" {
                tags "Database"
            }
            bs = container "Blob Storage"
        }
    
        u -> ss.wa "Uses"
        ss.wa -> ss.db "Reads from and writes to"
        ss.wa -> ss.bs "Writes audio files to"
    }

    views {
        systemContext ss "Diagram1" {
            include *
            autolayout lr
        }

        container ss "Diagram2" {
            include *
            autolayout lr
        }
    }
}