# Building ScribeBox

This guide walks you through building the ScribeBox USB image from source.
You only need to do this once — the resulting image can be flashed to as
many USB sticks as you want.

**Time required:** 15-45 minutes (mostly downloading models and compiling)

---

## Table of Contents

- [What You Need](#what-you-need)
- [Building on Mac](#building-on-mac)
- [Building on Linux](#building-on-linux)
- [Building on Windows](#building-on-windows)
- [Flashing to USB](#flashing-to-usb)
- [Testing Without a USB Stick](#testing-without-a-usb-stick)
- [Troubleshooting](#troubleshooting)
- [Advanced: Building Without Docker](#advanced-building-without-docker)
- [Advanced: Custom Model Selection](#advanced-custom-model-selection)

---

## What You Need

**To build the image (on your main computer):**
- [Docker Desktop](https://docker.com/products/docker-desktop) (free) — Mac, Windows, or Linux
- About **10 GB of free disk space** (3.4 GB for models + build files)
- Internet connection (to download models, one-time only)

**To use the image (on the target computer):**
- A **16 GB or larger USB stick** (USB 3.0 recommended)
- A tool to flash the image: [Balena Etcher](https://etcher.balena.io) (free, any platform) or `dd` (command line)

---

## Building on Mac

### 1. Install Docker Desktop

If you don't have Docker, install it:

**Option A — Homebrew (if you use it):**
```bash
brew install --cask docker
```

**Option B — Direct download:**
Go to https://docker.com/products/docker-desktop and download Docker Desktop
for Mac. Open the `.dmg` file and drag Docker to your Applications folder.

Open Docker Desktop from your Applications folder. Wait for the whale icon
to appear in your menu bar and stop animating — that means Docker is ready.

### 2. Get the ScribeBox Source Code

Open **Terminal** (find it in Applications > Utilities > Terminal).

```bash
# Go to your home folder (or wherever you want to put it)
cd ~

# Download the source code
git clone https://github.com/jasontitus/ScribeBox.git

# Go into the project folder
cd ScribeBox
```

If you don't have `git`, install it first:
```bash
xcode-select --install
```

### 3. Build

```bash
./build.sh
```

This will:
1. Download 7 AI models (~3.4 GB) — takes a few minutes on fast internet
2. Build a Docker container with all the build tools
3. Compile the whisper.cpp speech engine inside the container
4. Create the bootable USB image

When it finishes, you'll see:

```
  Build complete!
  Image: build/scribebox.img
```

### 4. Flash to USB

**Easiest: Use Balena Etcher**

1. Download [Balena Etcher](https://etcher.balena.io)
2. Open Etcher
3. Click "Flash from file" and select `build/scribebox.img`
4. Plug in your USB stick and select it
5. Click "Flash!"
6. Wait for it to finish. Done.

**Alternative: Use `dd` in Terminal**

```bash
# List your disks to find the USB stick
diskutil list

# Look for your USB stick — it will be something like:
#   /dev/disk2 (external, physical):
#   *16.0 GB ...

# Unmount it (replace disk2 with your actual disk number)
diskutil unmountDisk /dev/disk2

# Write the image (replace disk2 — be VERY careful to pick the right disk!)
sudo dd if=build/scribebox.img of=/dev/rdisk2 bs=4m

# Eject when done
diskutil eject /dev/disk2
```

**WARNING:** The `dd` command will erase whatever disk you point it at.
Double-check the disk number. If you're not sure, use Balena Etcher instead —
it's safer and won't let you accidentally erase your main drive.

---

## Building on Linux

### 1. Install Docker (if you don't have it)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in for the group change to take effect, then verify:
```bash
docker run hello-world
```

### 2. Get the Source Code and Build

```bash
git clone https://github.com/jasontitus/ScribeBox.git
cd ScribeBox
./build.sh
```

**Alternative: Build without Docker (Linux only)**

If you prefer not to use Docker, you can build natively:

```bash
sudo apt install debootstrap grub-pc-bin parted dosfstools e2fsprogs \
    cmake build-essential python3 python3-pip curl
sudo ./build.sh
```

### 3. Flash to USB

```bash
# Find your USB stick
lsblk

# Flash (replace /dev/sdX with your USB device — e.g., /dev/sdb)
sudo dd if=build/scribebox.img of=/dev/sdX bs=4M status=progress
sync
```

**WARNING:** Make sure `/dev/sdX` is your USB stick, not your hard drive.
`lsblk` shows the size of each device — your USB stick is the one that
matches (e.g., 16 GB).

---

## Building on Windows

### 1. Install Docker Desktop

Download and install [Docker Desktop for Windows](https://docker.com/products/docker-desktop).

You'll need either **WSL 2** (Windows Subsystem for Linux) or **Hyper-V**.
Docker Desktop will guide you through enabling one of these during installation.

Restart your computer when prompted.

### 2. Get the Source Code

**Option A — Git Bash (recommended):**

Install [Git for Windows](https://git-scm.com/download/win) if you don't
have it. Open **Git Bash** from the Start menu.

```bash
cd ~
git clone https://github.com/jasontitus/ScribeBox.git
cd ScribeBox
./build.sh
```

**Option B — WSL 2:**

Open a WSL terminal (Ubuntu) from the Start menu:

```bash
cd ~
git clone https://github.com/jasontitus/ScribeBox.git
cd ScribeBox
./build.sh
```

### 3. Flash to USB

Download [Balena Etcher](https://etcher.balena.io) for Windows. Open it,
select the `build/scribebox.img` file, select your USB drive, and flash.

You can also use [Rufus](https://rufus.ie):
1. Open Rufus
2. Select your USB device
3. Click SELECT and choose `build/scribebox.img`
4. Click START
5. Choose "Write in DD Image mode" when prompted

---

## Testing Without a USB Stick

You can test the ScribeBox image in a virtual machine before flashing it.

### Mac — UTM (Free)

1. Install [UTM](https://mac.getutm.app) (free from the website, or `brew install --cask utm`)
2. Run:
   ```bash
   ./scripts/create-test-vm.sh
   ```
3. This creates `build/ScribeBox-Test.utm` — double-click it to open in UTM
4. Click the Play button to boot

### Linux — QEMU

```bash
# Install QEMU
sudo apt install qemu-system-x86

# Run the test VM
./scripts/create-test-vm.sh
```

### Windows — VirtualBox

1. Install [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
2. Convert the raw image to VDI:
   ```
   VBoxManage convertfromraw build/scribebox.img build/scribebox.vdi --format VDI
   ```
3. Create a new VM: Linux, Debian 64-bit, 2 GB RAM
4. Use the `.vdi` file as the hard disk
5. Boot the VM

---

## Troubleshooting

### "Docker is not running"

- **Mac:** Open Docker Desktop from your Applications folder. Wait for the
  whale icon in the menu bar to stop animating.
- **Linux:** Run `sudo systemctl start docker`
- **Windows:** Open Docker Desktop from the Start menu. Wait for it to say
  "Docker Desktop is running."

### Build fails with "No space left on device"

You need about 10 GB of free disk space. The AI models alone are 3.4 GB.
Free up space and try again.

### "Permission denied" when flashing

- **Mac/Linux:** Use `sudo` before the `dd` command
- **Windows:** Run Balena Etcher as Administrator

### The computer won't boot from USB

Different computers use different keys to open the boot menu:

| Manufacturer | Boot Menu Key |
|-------------|---------------|
| Dell | F12 |
| HP | F9 or Esc |
| Lenovo | F12 or Fn+F12 |
| ASUS | F8 or Esc |
| Acer | F12 |
| Toshiba | F12 or F2 |
| Samsung | F2 or F10 |
| Apple Mac | Hold Option key at startup |
| Generic | Try F12, F2, Esc, or Del |

If the boot menu doesn't show the USB stick:
1. Enter BIOS/UEFI setup (usually Del or F2 during startup)
2. Find "Boot Order" or "Boot Priority"
3. Move USB to the top, or enable "USB Boot"
4. Some newer machines need "Legacy Boot" or "CSM" enabled
5. Disable "Secure Boot" if the USB won't appear

### Model download is slow or fails

The models download from Hugging Face (huggingface.co). If it's slow:
- Check your internet connection
- Try again later (the server may be busy)
- Already-downloaded models are skipped, so re-running is safe

### Build works but no audio in ScribeBox

- Make sure the laptop has a working microphone
- Try plugging in an external USB microphone
- In a VM, you need to pass through audio (UTM and QEMU support this;
  VirtualBox needs guest additions)

---

## Advanced: Building Without Docker

If you're on Linux and prefer not to use Docker, you can build natively.
You need root access and these packages:

```bash
# Debian/Ubuntu
sudo apt install debootstrap grub-pc-bin grub-efi-amd64-bin parted \
    dosfstools e2fsprogs cmake build-essential python3 python3-pip \
    python3-numpy curl wget git

# Build everything step by step:
./scripts/download-models.sh          # Download AI models
./scripts/build-whisper-cpp.sh        # Compile whisper.cpp
sudo ./scripts/build-image.sh         # Create bootable image (needs root)
```

---

## Advanced: Custom Model Selection

By default, ScribeBox downloads 7 English-optimized models. You can customize
which models are included.

### Download only specific models

Edit `scripts/download-models.sh` and comment out models you don't want:

```bash
MODELS=(
    "ggml-tiny.en.bin"              # Keep — needed for old hardware
    "ggml-base.en.bin"              # Keep — good default
    # "ggml-small.en-q5_1.bin"      # Skip — save space
    "ggml-small.en.bin"             # Keep
    # "ggml-medium.en-q5_0.bin"     # Skip — save space
    # "ggml-large-v3-turbo-q5_0.bin"  # Skip
    # "ggml-large-v3-turbo.bin"     # Skip — save 1.6 GB
)
```

### Add multilingual models

Uncomment the multilingual models at the bottom of the file:

```bash
    "ggml-tiny.bin"                 # Multilingual tiny
    "ggml-base.bin"                 # Multilingual base
    "ggml-small.bin"                # Multilingual small
```

These support 99 languages but are slightly less accurate for English
compared to the `.en` versions.

### Minimal USB (just tiny.en, ~2 GB image)

If you only need basic transcription on old hardware:

```bash
# Download just the tiny model
mkdir -p models
curl -L -o models/ggml-tiny.en.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
```

Then edit `scripts/build-image.sh` and reduce `IMAGE_SIZE_MB` to `4096`.
