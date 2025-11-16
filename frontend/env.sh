#!/usr/bin/env sh
# ================================================================================
# File: env.sh
# Description: Replaces environment variables in asset files.
# Usage: Run this script in your terminal, ensuring APP_PREFIX and ASSET_DIRS are set.
# ================================================================================


# Set the exit flag to exit immediately if any command fails
set -e

# Check if APP_PREFIX is set
: "${APP_PREFIX:?APP_PREFIX must be set (e.g. APP_PREFIX='APP_PREFIX_')}"

# Check if ASSET_DIRS is set
: "${ASSET_DIR:?Must set ASSET_DIR to one path}"

# Check if the directory exists
if [ ! -d "$ASSET_DIR" ]; then
    # If not, display a warning message and skip to the next iteration
    echo "Warning: directory '$ASSET_DIR' not found, skipping."
    continue
fi

# Display the current directory being scanned
echo "Scanning directory: $ASSET_DIR"

# Iterate through each environment variable that starts with APP_PREFIX
env | grep "^${APP_PREFIX}" | while IFS='=' read -r key value; do

    # Skip the APP_PREFIX variable itself
    if [ "$key" = "APP_PREFIX" ]; then
        continue
    fi

    # Modify the key to replace APP_PREFIX with PREFIX_
    new_key="PREFIX_${key#${APP_PREFIX}}"

    # Display the variable being replaced
    echo "  • Using ${new_key} → ${value}"

    # Use find and sed to replace the variable in all files within the directory
    find "$ASSET_DIR" -type f \
        -exec sed -i "s|${new_key}|${value}|g" {} +
done