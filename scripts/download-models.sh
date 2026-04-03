#!/bin/bash
# Download Whisper GGML models for ScribeBox
# Run this once with internet access before building the USB image.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${1:-$SCRIPT_DIR/../models}"

mkdir -p "$MODELS_DIR"

BASE_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

# Practical model set (~3.6GB total):
# - English-only models (most users transcribing in English)
# - Quantized variants where they save significant RAM
# - large-v3-turbo instead of full large-v3 (faster AND smaller)
# - Multilingual users: uncomment the multilingual models below
MODELS=(
    "ggml-tiny.en.bin"          #   75 MB - 2GB RAM machines
    "ggml-base.en.bin"          #  142 MB - 4GB RAM machines
    "ggml-small.en-q5_1.bin"    #  190 MB - 4GB RAM, better quality
    "ggml-small.en.bin"         #  466 MB - 4-8GB RAM
    "ggml-medium.en-q5_0.bin"   #  540 MB - 8GB RAM
    "ggml-large-v3-turbo-q5_0.bin"  #  600 MB - 8GB+ RAM
    "ggml-large-v3-turbo.bin"   #  1.6 GB - 8GB+ RAM, best quality
    # Uncomment for multilingual support (adds ~750 MB):
    # "ggml-tiny.bin"
    # "ggml-base.bin"
    # "ggml-small.bin"
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
