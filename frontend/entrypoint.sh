#!/bin/sh

# Set the exit flag to exit immediately if any command fails
set -e

# Environment variable validation and defaults
echo "=> Starting frontend container..."

# Environment variable checks
echo "Checking environment variables..."

# Check required environment variables
check_env_var() {
    local var_name=$1
    local default_value=$2
    local current_value=$(eval echo \$$var_name)
    
    if [ -z "$current_value" ]; then
        if [ -n "$default_value" ]; then
            export $var_name="$default_value"
            echo "$var_name not set, using default: $default_value"
        else
            echo "L Required environment variable $var_name is not set"
            exit 1
        fi
    else
        echo "$var_name: $current_value"
    fi
}


# Replace all the vars
/docker-entrypoint.d/env.sh


# Backend API URL - required for WebRTC connections
check_env_var "${APP_PREFIX}BACKEND_URL"
check_env_var "${APP_PREFIX}SITE_URL"
check_env_var "${APP_PREFIX}OIDC_AUTHORITY"
check_env_var "${APP_PREFIX}OIDC_CLIENT_ID"

# Validate nginx configuration
echo "Validating nginx configuration..."
nginx -t

if [ $? -ne 0 ]; then
    echo "Nginx configuration validation failed"
    exit 1
fi

# Start nginx
echo "Starting nginx..."
exec nginx -g "daemon off;"