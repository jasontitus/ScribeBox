# ScribeBox

**A USB-bootable Linux OS that turns any laptop into a dedicated transcription device.**

Plug in, reboot, transcribe. No internet required.

## Features

- **Instant boot** into a clean transcription interface
- **Real-time transcription** powered by whisper.cpp (CPU-optimized)
- **Rolling 2-minute summaries** using extractive summarization (TextRank)
- **Speaker diarization** with lightweight voice activity detection
- **Configurable UI** - font size, themes, layout options
- **Hardware auto-detection** - automatically selects the best Whisper model
- **Built-in benchmark** - test which models your hardware can handle in real-time
- **All models included on USB** - tiny, base, small, medium (+ quantized variants)
- **Preferences saved locally** on the USB drive
- **Works on 2010-2015 era laptops** with as little as 2GB RAM

## Target Hardware

| RAM   | Recommended Model | Real-time? | Quality |
|-------|-------------------|------------|---------|
| 2 GB  | tiny.en (75 MB)   | Yes        | Basic   |
| 4 GB  | base.en (142 MB)  | Yes        | Good    |
| 4 GB  | small.en-q5 (190 MB) | Borderline | Better |
| 8 GB  | small.en (466 MB) | Yes        | Great   |
| 8 GB+ | large-v3-turbo-q5 (548 MB) | Depends on CPU | Best |
| 16 GB | large-v3-turbo (1.6 GB) | Modern CPUs | Best |

**Included models (3.4 GB total):** tiny.en, base.en, small.en-q5, small.en,
medium.en-q5, large-v3-turbo-q5, large-v3-turbo. All English-optimized.
The built-in benchmark tool tests your hardware and recommends the best model.

### Minimum Hardware

- **CPU**: x86-64 with AVX (2011+). AVX2 (2013+) strongly recommended.
- **RAM**: 2 GB minimum (tiny.en). 4 GB recommended (base.en or small.en).
- **USB**: 16 GB stick (8 GB image).
- **Mac compatibility**: 2013 MacBook Pro or newer. 2011-2012 usable with tiny.en.

## Quick Start

### Building the USB Image

Works on **Mac, Linux, and Windows** (via Docker):

```bash
# One command does everything:
./build.sh
```

That's it. The script will:
1. Detect your platform (Docker, native Linux, etc.)
2. Download the 7 Whisper models (~3.4 GB, one-time)
3. Compile whisper.cpp with portable CPU optimizations
4. Build an 8 GB bootable USB image

Output: `build/scribebox.img`

**Requirements:** Just [Docker](https://docker.com/products/docker-desktop).
On Linux you can also run `sudo ./build.sh` without Docker.

### Flashing to USB

```bash
# Linux
sudo dd if=build/scribebox.img of=/dev/sdX bs=4M status=progress

# Mac
diskutil list                    # Find your USB (e.g. disk2)
diskutil unmountDisk /dev/diskN
sudo dd if=build/scribebox.img of=/dev/rdiskN bs=4m
diskutil eject /dev/diskN

# Windows / Any platform
# Use Balena Etcher (free): https://etcher.balena.io
```

### Testing in a VM (no USB needed)

```bash
# Test with QEMU or UTM (Mac)
./scripts/create-test-vm.sh
```

On Mac, this creates a UTM VM bundle you can double-click to boot.
On Linux, it launches QEMU directly.

### Development (run without building an image)

```bash
# Install dependencies
pip install -r requirements.txt

# Build whisper.cpp
./scripts/build-whisper-cpp.sh

# Run the application
python -m scribebox
```

## Architecture

```
ScribeBox/
├── build.sh                # One-command build (auto-detects platform)
├── scribebox/              # Main Python application
│   ├── __main__.py         # Entry point
│   ├── app.py              # Main application controller
│   ├── transcriber.py      # whisper.cpp integration
│   ├── audio.py            # Audio capture (ALSA/sounddevice)
│   ├── summarizer.py       # Extractive summarization (TextRank)
│   ├── diarizer.py         # Speaker diarization (MFCC + clustering)
│   ├── benchmark.py        # Hardware benchmark tool
│   ├── preferences.py      # Settings management
│   └── ui/                 # UI components (GTK3)
│       ├── main_window.py  # Main window with header, transcript, summary
│       ├── transcript_view.py  # Scrolling transcript display
│       ├── summary_panel.py    # Rolling summary panel
│       ├── preferences_dialog.py # Settings dialog
│       └── theme.py        # Dark/light/high-contrast themes
├── docker/                 # Docker build environment
│   └── Dockerfile.build    # Debian-based builder image
├── configs/                # System configuration for bootable image
│   ├── systemd/            # Auto-start services
│   ├── xorg/               # Display configuration
│   └── skel/               # Default user skeleton
├── scripts/                # Build and utility scripts
│   ├── build-image.sh      # Build bootable USB image
│   ├── build-whisper-cpp.sh  # Compile whisper.cpp
│   ├── build-image-docker.sh # Docker-based image builder
│   ├── download-models.sh    # Download Whisper models
│   └── create-test-vm.sh     # Create UTM/QEMU test VM
├── tests/                  # Test suite (70 tests)
├── models/                 # Pre-loaded Whisper models (3.4 GB, 7 models)
└── requirements.txt        # Python dependencies
```

## How It Works

1. **Boot**: Minimal Debian-based Linux boots from USB, auto-logs in, starts ScribeBox
2. **Audio**: Captures microphone input via ALSA at 16kHz mono
3. **Transcription**: Streams audio chunks to whisper.cpp for real-time transcription
4. **Display**: Shows transcription in a large, readable font with auto-scroll
5. **Summary**: Every 2 minutes, runs TextRank extractive summarization on recent text
6. **Diarization**: Uses Silero VAD + spectral clustering to identify speaker changes
7. **Save**: Transcripts auto-save to the USB drive's data partition

## Preferences

Saved to `/data/scribebox/preferences.json` on the USB drive:

- **Whisper model**: tiny.en, base.en, small.en, medium.en (+ quantized)
- **Theme**: Dark / Light / High Contrast
- **Font size**: 14-48pt
- **Layout**: Full transcript / Split (transcript + summary) / Three-panel
- **Diarization**: On / Off
- **Auto-save interval**: 30s / 1m / 5m
- **Language**: English (default), or auto-detect

## License

MIT
