#!/bin/bash
# ============================================================
#  ScribeBox — One-Command Build
# ============================================================
#
#  Just run:  ./build.sh
#
#  This script detects your environment and does the right thing:
#    - Docker available?  → Builds inside a container (works everywhere)
#    - Linux with root?   → Builds natively (faster)
#    - Otherwise          → Tells you what to install
#
#  Output:  build/scribebox.img
#
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║       ScribeBox USB Builder          ║"
echo "  ║  Transcription appliance for any PC  ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Pass through arguments
ARGS="$@"

# Detect best build method
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    echo "  Using Docker build (recommended, works on any platform)"
    echo ""
    exec ./scripts/build-image-docker.sh $ARGS

elif [ "$(uname)" = "Linux" ] && [ "$(id -u)" -eq 0 ]; then
    echo "  Using native Linux build"
    echo ""

    # Check for models
    if [ -z "$(ls models/ggml-*.bin 2>/dev/null)" ]; then
        echo "  Downloading models first..."
        ./scripts/download-models.sh
    fi

    # Check for whisper binary
    if [ ! -f "bin/whisper-cli" ]; then
        echo "  Building whisper.cpp..."
        SCRIBEBOX_PORTABLE=1 ./scripts/build-whisper-cpp.sh
    fi

    exec ./scripts/build-image.sh

elif [ "$(uname)" = "Linux" ]; then
    echo "  Linux detected but not running as root."
    echo ""
    echo "  Option 1 (recommended): Install Docker and re-run ./build.sh"
    echo "    curl -fsSL https://get.docker.com | sh"
    echo ""
    echo "  Option 2: Run with sudo"
    echo "    sudo ./build.sh"
    exit 1

elif [ "$(uname)" = "Darwin" ]; then
    if ! command -v docker &>/dev/null; then
        echo "  Mac detected. Docker required to build the USB image."
        echo ""
        echo "  Install Docker Desktop:"
        echo "    brew install --cask docker"
        echo "    (or download from https://docker.com/products/docker-desktop)"
        echo ""
        echo "  Then re-run:  ./build.sh"
        exit 1
    fi
    echo "  Docker found but daemon not running. Start Docker Desktop and retry."
    exit 1

else
    echo "  Windows detected (or unknown OS)."
    echo ""
    echo "  Install Docker Desktop:"
    echo "    https://docker.com/products/docker-desktop"
    echo ""
    echo "  Then run in Git Bash / WSL:"
    echo "    ./build.sh"
    exit 1
fi
