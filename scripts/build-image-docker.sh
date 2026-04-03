#!/bin/bash
# ============================================================
#  ScribeBox — Docker-based USB Image Builder
# ============================================================
#
#  Builds the complete bootable USB image inside a Docker container.
#  Works on Mac, Linux, and Windows (with Docker Desktop).
#
#  Usage:
#    ./scripts/build-image-docker.sh              # Build everything
#    ./scripts/build-image-docker.sh --skip-models # Build without re-downloading models
#    ./scripts/build-image-docker.sh --shell       # Drop into the build container
#
#  Output:
#    build/scribebox.img  — bootable USB image, ready to dd or flash
#
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
IMAGE_NAME="scribebox-builder"
CONTAINER_NAME="scribebox-build"
OUTPUT_DIR="$PROJECT_DIR/build"

SKIP_MODELS=false
SHELL_MODE=false

for arg in "$@"; do
    case "$arg" in
        --skip-models) SKIP_MODELS=true ;;
        --shell) SHELL_MODE=true ;;
        --help|-h)
            echo "Usage: $0 [--skip-models] [--shell]"
            echo ""
            echo "  --skip-models  Skip model download (use existing models/)"
            echo "  --shell        Drop into the build container for debugging"
            exit 0
            ;;
    esac
done

# ─── Preflight checks ───

if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker is not installed."
    echo ""
    echo "Install Docker:"
    echo "  Mac:     brew install --cask docker   (or https://docker.com/products/docker-desktop)"
    echo "  Linux:   curl -fsSL https://get.docker.com | sh"
    echo "  Windows: https://docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "ERROR: Docker daemon is not running."
    echo ""
    echo "Start Docker:"
    echo "  Mac/Windows: Open Docker Desktop"
    echo "  Linux:       sudo systemctl start docker"
    exit 1
fi

echo "========================================================"
echo "  ScribeBox USB Image Builder (Docker)"
echo "========================================================"
echo ""

# ─── Step 1: Download models (runs on host — avoids re-downloading in container) ───

if [ "$SKIP_MODELS" = false ]; then
    echo "[1/4] Downloading Whisper models..."
    "$SCRIPT_DIR/download-models.sh"
    echo ""
else
    echo "[1/4] Skipping model download (--skip-models)"
    if [ ! -d "$PROJECT_DIR/models" ] || [ -z "$(ls "$PROJECT_DIR/models"/ggml-*.bin 2>/dev/null)" ]; then
        echo "  WARNING: No models found in models/. The USB image needs models."
        echo "  Run without --skip-models, or manually run: ./scripts/download-models.sh"
    fi
    echo ""
fi

# ─── Step 2: Build the Docker image ───

echo "[2/4] Building Docker build environment..."
docker build -t "$IMAGE_NAME" -f "$PROJECT_DIR/docker/Dockerfile.build" "$PROJECT_DIR/docker/" 2>&1 | \
    while IFS= read -r line; do echo "  $line"; done
echo "  Done."
echo ""

# ─── Step 3: Build whisper.cpp + USB image inside container ───

mkdir -p "$OUTPUT_DIR"

if [ "$SHELL_MODE" = true ]; then
    echo "Dropping into build container shell..."
    echo "  Run these commands to build manually:"
    echo "    /build/scribebox/scripts/build-whisper-cpp.sh"
    echo "    /build/scribebox/scripts/build-image.sh"
    echo ""
    docker run -it --rm --privileged \
        -v "$PROJECT_DIR:/build/scribebox:ro" \
        -v "$OUTPUT_DIR:/output" \
        "$IMAGE_NAME" \
        /bin/bash
    exit 0
fi

echo "[3/4] Compiling whisper.cpp and building USB image..."
echo "  This takes 10-30 minutes depending on your machine."
echo ""

# Run the build inside a privileged container (needed for losetup/mount)
# Mount project read-only, output directory read-write
docker run --rm --privileged \
    --name "$CONTAINER_NAME" \
    -v "$PROJECT_DIR:/build/scribebox:ro" \
    -v "$OUTPUT_DIR:/output" \
    "$IMAGE_NAME" \
    /bin/bash -c '
        set -e

        # Copy project to writable location
        cp -a /build/scribebox /tmp/scribebox
        cd /tmp/scribebox

        echo "  [a] Building whisper.cpp..."
        SCRIBEBOX_PORTABLE=1 ./scripts/build-whisper-cpp.sh 2>&1 | \
            sed "s/^/      /"

        echo ""
        echo "  [b] Building bootable USB image..."
        ./scripts/build-image.sh 2>&1 | \
            sed "s/^/      /"

        echo ""
        echo "  [c] Copying image to output..."
        cp build/scribebox.img /output/scribebox.img
        echo "  Done."
    '

# ─── Step 4: Done ───

echo ""
echo "========================================================"
echo "  Build complete!"
echo ""
echo "  Image: $OUTPUT_DIR/scribebox.img"
echo "  Size:  $(du -h "$OUTPUT_DIR/scribebox.img" 2>/dev/null | cut -f1)"
echo ""
echo "  Flash to USB:"
echo ""
echo "  Linux:"
echo "    sudo dd if=$OUTPUT_DIR/scribebox.img of=/dev/sdX bs=4M status=progress"
echo ""
echo "  Mac:"
echo "    diskutil list                              # find your USB (e.g. disk2)"
echo "    diskutil unmountDisk /dev/diskN"
echo "    sudo dd if=$OUTPUT_DIR/scribebox.img of=/dev/rdiskN bs=4m"
echo "    diskutil eject /dev/diskN"
echo ""
echo "  Windows:"
echo "    Use Balena Etcher: https://etcher.balena.io"
echo "    Or Rufus:          https://rufus.ie"
echo ""
echo "  Any platform:"
echo "    Balena Etcher (free): https://etcher.balena.io"
echo "========================================================"
