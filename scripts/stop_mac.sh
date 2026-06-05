#!/usr/bin/env bash
CONTAINER_NAME="finally"

if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
    echo "Stopping FinAlly..."
    docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
    echo "Stopped. Data volume preserved."
else
    echo "FinAlly is not running."
fi
