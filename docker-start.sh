#!/bin/bash
# Quick start script for local-console Docker on macOS/Linux

set -e

echo ""
echo "============================================"
echo "   Local Console - Docker Quick Start"
echo "============================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/3] Building Docker image..."
if docker build -t local-console:latest . > /dev/null 2>&1; then
    echo "[OK] Image built successfully"
else
    echo "Build failed!"
    docker build -t local-console:latest .
    exit 1
fi

echo ""
echo "[2/3] Starting container..."
if docker-compose down > /dev/null 2>&1; then
    :
fi
if docker-compose up -d; then
    echo "[OK] Container started"
else
    echo "Failed to start container"
    docker-compose up
    exit 1
fi

echo ""
echo "[3/3] Waiting for service to be ready..."
sleep 3

echo ""
echo "============================================"
echo "   Console is ready!"
echo "============================================"
echo ""
echo "Access the console at: http://localhost:9600"
echo ""
echo "Useful commands:"
echo "  - View logs:     docker-compose logs -f"
echo "  - Stop service:  docker-compose down"
echo "  - Restart:       docker-compose restart"
echo ""
