#!/bin/bash
# ============================================================
#  Create a UTM/QEMU VM to test the ScribeBox image
# ============================================================
#
#  Tests the USB image without needing real hardware.
#  Works with:
#    - UTM (Mac) — creates a .utm bundle
#    - QEMU (Linux/Mac/Windows) — runs directly
#
#  Usage:
#    ./scripts/create-test-vm.sh              # Auto-detect best method
#    ./scripts/create-test-vm.sh --qemu       # Force QEMU
#    ./scripts/create-test-vm.sh --utm        # Create UTM config
#
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
IMAGE="$PROJECT_DIR/build/scribebox.img"

if [ ! -f "$IMAGE" ]; then
    echo "ERROR: No image found at $IMAGE"
    echo "Run ./build.sh first to create the USB image."
    exit 1
fi

IMAGE_ABS="$(cd "$(dirname "$IMAGE")" && pwd)/$(basename "$IMAGE")"

# ─── QEMU method ───

run_qemu() {
    if ! command -v qemu-system-x86_64 &>/dev/null; then
        echo "ERROR: qemu-system-x86_64 not found."
        echo ""
        echo "Install QEMU:"
        echo "  Mac:   brew install qemu"
        echo "  Linux: sudo apt install qemu-system-x86"
        echo "  Arch:  sudo pacman -S qemu-full"
        exit 1
    fi

    echo "Starting ScribeBox in QEMU..."
    echo "  Image: $IMAGE_ABS"
    echo "  RAM:   2048 MB"
    echo "  CPU:   2 cores"
    echo ""
    echo "  Close the QEMU window to stop the VM."
    echo "  Press Ctrl+Alt+G to release mouse capture."
    echo ""

    qemu-system-x86_64 \
        -drive file="$IMAGE_ABS",format=raw,if=virtio \
        -m 2048 \
        -smp 2 \
        -cpu host \
        -enable-kvm 2>/dev/null || \
    qemu-system-x86_64 \
        -drive file="$IMAGE_ABS",format=raw,if=virtio \
        -m 2048 \
        -smp 2 \
        -cpu max \
        -audiodev coreaudio,id=audio0 2>/dev/null || \
    qemu-system-x86_64 \
        -drive file="$IMAGE_ABS",format=raw,if=virtio \
        -m 2048 \
        -smp 2 \
        -cpu max
}

# ─── UTM method (Mac) ───

create_utm() {
    UTM_DIR="$PROJECT_DIR/build/ScribeBox-Test.utm"

    echo "Creating UTM VM bundle..."

    # Convert raw image to QCOW2 (UTM prefers it)
    QCOW_IMAGE="$PROJECT_DIR/build/scribebox.qcow2"
    if command -v qemu-img &>/dev/null; then
        echo "  Converting image to QCOW2..."
        qemu-img convert -f raw -O qcow2 "$IMAGE_ABS" "$QCOW_IMAGE"
    else
        echo "  qemu-img not found, UTM will use raw image."
        echo "  For better performance: brew install qemu"
        QCOW_IMAGE=""
    fi

    # Create UTM directory structure
    mkdir -p "$UTM_DIR/Data"

    # Determine disk image to use
    if [ -n "$QCOW_IMAGE" ] && [ -f "$QCOW_IMAGE" ]; then
        cp "$QCOW_IMAGE" "$UTM_DIR/Data/scribebox.qcow2"
        DISK_NAME="scribebox.qcow2"
        DISK_INTERFACE="qcow2"
    else
        cp "$IMAGE_ABS" "$UTM_DIR/Data/scribebox.img"
        DISK_NAME="scribebox.img"
        DISK_INTERFACE="raw"
    fi

    # Create UTM plist config
    cat > "$UTM_DIR/config.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Name</key>
    <string>ScribeBox Test</string>
    <key>Notes</key>
    <string>ScribeBox USB image test VM. Boot from the virtual drive to test the transcription appliance.</string>
    <key>Backend</key>
    <string>QEMU</string>
    <key>System</key>
    <dict>
        <key>Architecture</key>
        <string>x86_64</string>
        <key>CPU</key>
        <string>max</string>
        <key>CPUCount</key>
        <integer>2</integer>
        <key>MemorySize</key>
        <integer>2048</integer>
    </dict>
    <key>Drives</key>
    <array>
        <dict>
            <key>Identifier</key>
            <string>drive0</string>
            <key>ImageName</key>
            <string>${DISK_NAME}</string>
            <key>ImageType</key>
            <string>Disk</string>
            <key>Interface</key>
            <string>VirtIO</string>
        </dict>
    </array>
    <key>Display</key>
    <dict>
        <key>ConsoleOnly</key>
        <false/>
    </dict>
    <key>Sound</key>
    <dict>
        <key>Enabled</key>
        <true/>
    </dict>
</dict>
</plist>
PLIST

    echo ""
    echo "  UTM VM created: $UTM_DIR"
    echo ""
    echo "  To test:"
    echo "    1. Open UTM"
    echo "    2. File → Import → select $UTM_DIR"
    echo "       (or double-click ScribeBox-Test.utm in Finder)"
    echo "    3. Click Play to boot"
    echo ""
    echo "  VM Settings: 2 cores, 2GB RAM, VirtIO disk, audio enabled"

    # Try to open UTM directly
    if [ "$(uname)" = "Darwin" ]; then
        echo ""
        read -p "  Open in UTM now? [Y/n] " answer
        if [ "$answer" != "n" ] && [ "$answer" != "N" ]; then
            open "$UTM_DIR" 2>/dev/null || echo "  Could not open UTM. Open it manually."
        fi
    fi
}

# ─── Auto-detect ───

METHOD=""
for arg in "$@"; do
    case "$arg" in
        --qemu) METHOD="qemu" ;;
        --utm) METHOD="utm" ;;
    esac
done

if [ -z "$METHOD" ]; then
    if [ "$(uname)" = "Darwin" ]; then
        # Mac: prefer UTM, fall back to QEMU
        if [ -d "/Applications/UTM.app" ] || command -v utmctl &>/dev/null; then
            METHOD="utm"
        elif command -v qemu-system-x86_64 &>/dev/null; then
            METHOD="qemu"
        else
            echo "To test the ScribeBox image on Mac, install one of:"
            echo ""
            echo "  UTM (recommended, free):"
            echo "    Download from https://mac.getutm.app"
            echo "    Or: brew install --cask utm"
            echo ""
            echo "  QEMU:"
            echo "    brew install qemu"
            echo ""
            echo "Then re-run this script."
            exit 1
        fi
    else
        # Linux/Windows: use QEMU
        METHOD="qemu"
    fi
fi

case "$METHOD" in
    qemu) run_qemu ;;
    utm) create_utm ;;
esac
