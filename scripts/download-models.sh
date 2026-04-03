#!/bin/bash
# Download Whisper GGML models for ScribeBox
# Run this once with internet access before building the USB image.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${1:-$SCRIPT_DIR/../models}"

mkdir -p "$MODELS_DIR"

BASE_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

# Models to download - these cover the useful range for 2010-2015 hardware
MODELS=(
    "ggml-tiny.en.bin"
    "ggml-tiny.bin"
    "ggml-base.en.bin"
    "ggml-base.bin"
    "ggml-small.en.bin"
    "ggml-small.bin"
    "ggml-small.en-q5_1.bin"
    "ggml-medium.en.bin"
    "ggml-medium.en-q5_0.bin"
)

echo "========================================"
echo "  ScribeBox Model Downloader"
echo "========================================"
echo
echo "Download directory: $MODELS_DIR"
echo "Models to download: ${#MODELS[@]}"
echo

total_size=0

for model in "${MODELS[@]}"; do
    dest="$MODELS_DIR/$model"

    if [ -f "$dest" ]; then
        size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null || echo 0)
        echo "  [SKIP] $model (already exists, $(( size / 1048576 )) MB)"
        total_size=$((total_size + size))
        continue
    fi

    echo "  [DOWNLOADING] $model ..."
    url="$BASE_URL/$model"

    if command -v wget &>/dev/null; then
        wget -q --show-progress -O "$dest" "$url"
    elif command -v curl &>/dev/null; then
        curl -L --progress-bar -o "$dest" "$url"
    else
        echo "    ERROR: Neither wget nor curl found!"
        exit 1
    fi

    if [ -f "$dest" ]; then
        size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null || echo 0)
        echo "    Done: $(( size / 1048576 )) MB"
        total_size=$((total_size + size))
    else
        echo "    FAILED to download $model"
    fi
done

echo
echo "========================================"
echo "  Download complete!"
echo "  Total size: $(( total_size / 1048576 )) MB"
echo "  Models in: $MODELS_DIR"
echo "========================================"
echo
echo "Available models:"
ls -lh "$MODELS_DIR"/ggml-*.bin 2>/dev/null || echo "  (none)"
