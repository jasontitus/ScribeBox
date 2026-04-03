#!/bin/bash
# Build whisper.cpp from source with CPU optimizations.
# Produces a statically-linked binary for the USB image.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
BUILD_DIR="$PROJECT_DIR/build/whisper-cpp"
INSTALL_DIR="${1:-$PROJECT_DIR/bin}"

echo "========================================"
echo "  Building whisper.cpp"
echo "========================================"

# Clone or update whisper.cpp
if [ -d "$BUILD_DIR" ]; then
    echo "  Updating existing whisper.cpp source..."
    cd "$BUILD_DIR"
    git pull --ff-only 2>/dev/null || true
else
    echo "  Cloning whisper.cpp..."
    mkdir -p "$(dirname "$BUILD_DIR")"
    git clone https://github.com/ggerganov/whisper.cpp.git "$BUILD_DIR"
    cd "$BUILD_DIR"
fi

# Detect CPU features for optimization flags
EXTRA_FLAGS=""
if grep -q "avx2" /proc/cpuinfo 2>/dev/null; then
    echo "  Detected AVX2 support"
    EXTRA_FLAGS="-mavx2 -mfma -mf16c"
elif grep -q "avx" /proc/cpuinfo 2>/dev/null; then
    echo "  Detected AVX support"
    EXTRA_FLAGS="-mavx"
elif grep -q "sse4" /proc/cpuinfo 2>/dev/null; then
    echo "  Detected SSE4 support"
    EXTRA_FLAGS="-msse4.1 -msse4.2"
elif grep -q "sse3" /proc/cpuinfo 2>/dev/null; then
    echo "  Detected SSE3 support"
    EXTRA_FLAGS="-msse3"
fi

# For maximum compatibility on the USB image, build with SSE3 minimum
# (all x86-64 CPUs from 2005+ have SSE3)
if [ -n "$SCRIBEBOX_PORTABLE" ]; then
    echo "  Building portable binary (SSE3 only)..."
    EXTRA_FLAGS="-msse3"
fi

echo "  Compiling with flags: $EXTRA_FLAGS"

# Build using CMake
mkdir -p build && cd build
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="$EXTRA_FLAGS" \
    -DCMAKE_CXX_FLAGS="$EXTRA_FLAGS" \
    -DWHISPER_BUILD_EXAMPLES=ON \
    -DWHISPER_BUILD_TESTS=OFF \
    -DBUILD_SHARED_LIBS=OFF

make -j"$(nproc)" whisper-cli

# Install
mkdir -p "$INSTALL_DIR"
cp bin/whisper-cli "$INSTALL_DIR/" 2>/dev/null || cp whisper-cli "$INSTALL_DIR/" 2>/dev/null || {
    # Try to find the binary
    BINARY=$(find . -name "whisper-cli" -type f -executable | head -1)
    if [ -n "$BINARY" ]; then
        cp "$BINARY" "$INSTALL_DIR/"
    else
        echo "  ERROR: Could not find compiled whisper-cli binary"
        exit 1
    fi
}

echo
echo "  whisper-cli installed to: $INSTALL_DIR/whisper-cli"
echo "  Build complete!"
