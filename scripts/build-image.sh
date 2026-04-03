#!/bin/bash
# Build the ScribeBox bootable USB image.
#
# Creates a Debian-based minimal Linux image with:
# - Minimal kernel + initramfs
# - X.org with modesetting driver (broad GPU compatibility)
# - Python 3 + GTK3 + ScribeBox application
# - whisper.cpp binary
# - Pre-loaded Whisper models
# - Persistent data partition for preferences and transcripts
#
# Requirements: debootstrap, grub, parted, mtools
# Must be run as root.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
BUILD_DIR="$PROJECT_DIR/build"
ROOTFS="$BUILD_DIR/rootfs"
IMAGE="$BUILD_DIR/scribebox.img"

# Image size: models ~3.4GB + system ~2GB + data partition ~2.5GB ≈ 8GB
# Use a 16GB USB stick for comfortable headroom with transcript storage
IMAGE_SIZE_MB=8192
SYSTEM_SIZE_MB=6144   # System + models (3.4GB models + 2GB OS + overhead)
DATA_SIZE_MB=2048     # Persistent data partition for transcripts & preferences

DEBIAN_RELEASE="bookworm"

# ─── Preflight checks ───
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root."
    echo "Usage: sudo $0"
    exit 1
fi

for cmd in debootstrap grub-install parted losetup mkfs.ext4 mkfs.vfat; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: Required command '$cmd' not found."
        echo "Install with: apt install debootstrap grub-pc-bin parted dosfstools"
        exit 1
    fi
done

# Check that models exist
if [ ! -d "$PROJECT_DIR/models" ] || [ -z "$(ls "$PROJECT_DIR/models"/ggml-*.bin 2>/dev/null)" ]; then
    echo "ERROR: No models found in $PROJECT_DIR/models/"
    echo "Run './scripts/download-models.sh' first."
    exit 1
fi

# Check that whisper-cli exists
WHISPER_BIN="$PROJECT_DIR/bin/whisper-cli"
if [ ! -f "$WHISPER_BIN" ]; then
    echo "ERROR: whisper-cli not found at $WHISPER_BIN"
    echo "Run './scripts/build-whisper-cpp.sh' first."
    exit 1
fi

echo "========================================================"
echo "  ScribeBox USB Image Builder"
echo "========================================================"
echo "  Image size:  ${IMAGE_SIZE_MB} MB"
echo "  System part: ${SYSTEM_SIZE_MB} MB"
echo "  Data part:   ${DATA_SIZE_MB} MB"
echo "  Debian:      ${DEBIAN_RELEASE}"
echo "========================================================"
echo

# ─── Create disk image ───
echo "[1/8] Creating disk image..."
mkdir -p "$BUILD_DIR"
rm -f "$IMAGE"
dd if=/dev/zero of="$IMAGE" bs=1M count="$IMAGE_SIZE_MB" status=progress

# ─── Partition the image ───
echo "[2/8] Partitioning..."
parted -s "$IMAGE" mklabel msdos
parted -s "$IMAGE" mkpart primary fat32 1MiB 512MiB        # EFI/boot
parted -s "$IMAGE" mkpart primary ext4 512MiB ${SYSTEM_SIZE_MB}MiB  # System
parted -s "$IMAGE" mkpart primary ext4 ${SYSTEM_SIZE_MB}MiB 100%     # Data
parted -s "$IMAGE" set 1 boot on

# Set up loop device
LOOP=$(losetup -f --show -P "$IMAGE")
echo "  Loop device: $LOOP"

cleanup() {
    echo "Cleaning up..."
    umount "$ROOTFS/data" 2>/dev/null || true
    umount "$ROOTFS/boot" 2>/dev/null || true
    umount "$ROOTFS/proc" 2>/dev/null || true
    umount "$ROOTFS/sys" 2>/dev/null || true
    umount "$ROOTFS/dev" 2>/dev/null || true
    umount "$ROOTFS" 2>/dev/null || true
    losetup -d "$LOOP" 2>/dev/null || true
}
trap cleanup EXIT

# Format partitions
mkfs.vfat -F 32 -n SCRIBBOOT "${LOOP}p1"
mkfs.ext4 -L scribebox "${LOOP}p2"
mkfs.ext4 -L scribedata "${LOOP}p3"

# ─── Bootstrap Debian ───
echo "[3/8] Bootstrapping Debian ${DEBIAN_RELEASE} (this takes a while)..."
mkdir -p "$ROOTFS"
mount "${LOOP}p2" "$ROOTFS"
mkdir -p "$ROOTFS/boot" "$ROOTFS/data"
mount "${LOOP}p1" "$ROOTFS/boot"
mount "${LOOP}p3" "$ROOTFS/data"

debootstrap --variant=minbase --include=\
linux-image-amd64,\
grub-pc,\
systemd,\
xorg,\
xserver-xorg-video-all,\
xinit,\
python3,\
python3-pip,\
python3-gi,\
python3-gi-cairo,\
gir1.2-gtk-3.0,\
python3-numpy,\
python3-scipy,\
alsa-utils,\
pulseaudio,\
fonts-dejavu-core,\
fonts-liberation,\
sudo,\
locales \
"$DEBIAN_RELEASE" "$ROOTFS" http://deb.debian.org/debian

# ─── Configure the system ───
echo "[4/8] Configuring system..."

# Mount virtual filesystems for chroot
mount --bind /proc "$ROOTFS/proc"
mount --bind /sys "$ROOTFS/sys"
mount --bind /dev "$ROOTFS/dev"

# Set hostname
echo "scribebox" > "$ROOTFS/etc/hostname"

# Configure locale
echo "en_US.UTF-8 UTF-8" > "$ROOTFS/etc/locale.gen"
chroot "$ROOTFS" locale-gen

# fstab
cat > "$ROOTFS/etc/fstab" << 'FSTAB'
# ScribeBox filesystem table
LABEL=scribebox  /       ext4  errors=remount-ro  0  1
LABEL=SCRIBBOOT  /boot   vfat  defaults           0  2
LABEL=scribedata /data   ext4  defaults           0  2
tmpfs            /tmp    tmpfs defaults,noatime    0  0
FSTAB

# Create scribebox user (no password, auto-login)
chroot "$ROOTFS" useradd -m -s /bin/bash -G audio,video,input,plugdev scribebox
chroot "$ROOTFS" passwd -d scribebox

# Auto-login on tty1
mkdir -p "$ROOTFS/etc/systemd/system/getty@tty1.service.d"
cp "$PROJECT_DIR/configs/systemd/scribebox-autologin.conf" \
   "$ROOTFS/etc/systemd/system/getty@tty1.service.d/autologin.conf"

# ─── Install ScribeBox application ───
echo "[5/8] Installing ScribeBox application..."

# Install Python dependencies
chroot "$ROOTFS" pip3 install --break-system-packages \
    sounddevice PyYAML sumy nltk webrtcvad librosa 2>/dev/null || \
chroot "$ROOTFS" pip3 install \
    sounddevice PyYAML sumy nltk webrtcvad librosa

# Copy application
mkdir -p "$ROOTFS/opt/scribebox"
cp -r "$PROJECT_DIR/scribebox" "$ROOTFS/opt/scribebox/"
cp "$PROJECT_DIR/requirements.txt" "$ROOTFS/opt/scribebox/"

# Make it importable
ln -sf /opt/scribebox/scribebox "$ROOTFS/usr/lib/python3/dist-packages/scribebox" 2>/dev/null || true

# Copy whisper binary
mkdir -p "$ROOTFS/opt/scribebox/bin"
cp "$WHISPER_BIN" "$ROOTFS/opt/scribebox/bin/whisper-cli"
chmod +x "$ROOTFS/opt/scribebox/bin/whisper-cli"
ln -sf /opt/scribebox/bin/whisper-cli "$ROOTFS/usr/local/bin/whisper-cli"

# Copy models
echo "[6/8] Copying Whisper models (this may take a while)..."
mkdir -p "$ROOTFS/opt/scribebox/models"
cp "$PROJECT_DIR"/models/ggml-*.bin "$ROOTFS/opt/scribebox/models/"
echo "  Copied $(ls "$ROOTFS/opt/scribebox/models/"ggml-*.bin | wc -l) models"

# Copy configs
cp "$PROJECT_DIR/configs/xorg/xorg.conf" "$ROOTFS/etc/X11/xorg.conf"
cp "$PROJECT_DIR/configs/skel/.xinitrc" "$ROOTFS/home/scribebox/.xinitrc"
cp "$PROJECT_DIR/configs/skel/.bash_profile" "$ROOTFS/home/scribebox/.bash_profile"
chroot "$ROOTFS" chown -R scribebox:scribebox /home/scribebox

# Create data directory with correct permissions
mkdir -p "$ROOTFS/data/scribebox/transcripts"
chroot "$ROOTFS" chown -R scribebox:scribebox /data/scribebox

# Download NLTK data for summarization (punkt tokenizer)
chroot "$ROOTFS" python3 -c "import nltk; nltk.download('punkt', download_dir='/usr/share/nltk_data')" 2>/dev/null || true

# ─── Install bootloader ───
echo "[7/8] Installing GRUB bootloader..."

cat > "$ROOTFS/etc/default/grub" << 'GRUBCONF'
GRUB_DEFAULT=0
GRUB_TIMEOUT=1
GRUB_DISTRIBUTOR="ScribeBox"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash loglevel=3"
GRUB_CMDLINE_LINUX=""
GRUB_DISABLE_OS_PROBER=true
GRUBCONF

chroot "$ROOTFS" grub-install --target=i386-pc --boot-directory=/boot "$LOOP"
chroot "$ROOTFS" update-grub

# ─── Cleanup ───
echo "[8/8] Cleaning up..."
chroot "$ROOTFS" apt-get clean
rm -rf "$ROOTFS/var/cache/apt/archives"/*.deb
rm -rf "$ROOTFS/tmp/*"

# Unmount
umount "$ROOTFS/proc"
umount "$ROOTFS/sys"
umount "$ROOTFS/dev"
umount "$ROOTFS/data"
umount "$ROOTFS/boot"
umount "$ROOTFS"
losetup -d "$LOOP"
trap - EXIT

echo
echo "========================================================"
echo "  Build complete!"
echo "  Image: $IMAGE"
echo "  Size:  $(du -h "$IMAGE" | cut -f1)"
echo ""
echo "  Write to USB drive:"
echo "    sudo dd if=$IMAGE of=/dev/sdX bs=4M status=progress"
echo ""
echo "  Or use Balena Etcher / Rufus to flash the image."
echo "========================================================"
