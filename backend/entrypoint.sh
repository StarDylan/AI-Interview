#!/bin/sh
set -e

echo "=> Starting backend container..."

# Ensure data directory exists
mkdir -p /app/data

# Check if database exists
if [ ! -f "/app/data/database.sqlite3" ]; then
    echo "Database not found. Running Alembic migrations..."
    uv run alembic upgrade head
    echo "✓ Database initialized successfully"
else
    echo "Database found. Checking for pending migrations..."
    uv run alembic upgrade head
    echo "✓ Database up to date"
fi

echo "Starting application..."
exec uv run src/main.py
