#!/usr/bin/env bash
set -e

CONTAINER_NAME="finally"
IMAGE_NAME="finally"
PORT=8000

# Build if --build flag or image doesn't exist
if [[ "$1" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building FinAlly Docker image..."
    docker build -t "$IMAGE_NAME" "$(dirname "$0")/.."
fi

# Stop existing container if running
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
fi

echo "Starting FinAlly..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8000" \
    -v finally-data:/app/db \
    --env-file "$(dirname "$0")/../.env" \
    "$IMAGE_NAME"

echo ""
echo "FinAlly is running at http://localhost:$PORT"
echo "  Stop with: ./scripts/stop_mac.sh"

# Open browser on macOS
if command -v open &>/dev/null; then
    sleep 2
    open "http://localhost:$PORT"
fi
