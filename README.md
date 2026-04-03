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

```bash
# 1. Download whisper.cpp models (requires internet, one-time)
./scripts/download-models.sh

# 2. Build the bootable USB image
sudo ./scripts/build-image.sh

# 3. Write to USB drive (replace /dev/sdX)
sudo dd if=build/scribebox.img of=/dev/sdX bs=4M status=progress
```

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
├── scribebox/              # Main Python application
│   ├── __main__.py         # Entry point
│   ├── app.py              # Main application window
│   ├── transcriber.py      # whisper.cpp integration
│   ├── audio.py            # Audio capture (ALSA)
│   ├── summarizer.py       # Extractive summarization (TextRank)
│   ├── diarizer.py         # Speaker diarization (VAD + clustering)
│   ├── benchmark.py        # Hardware benchmark tool
│   ├── preferences.py      # Settings management
│   └── ui/                 # UI components
│       ├── main_window.py  # GTK main window
│       ├── transcript_view.py  # Scrolling transcript display
│       ├── summary_panel.py    # Rolling summary panel
│       ├── preferences_dialog.py # Settings dialog
│       └── theme.py        # Theming support
├── configs/                # System configuration for bootable image
│   ├── systemd/            # Auto-start services
│   ├── xorg/               # Display configuration
│   └── skel/               # Default user skeleton
├── scripts/                # Build and utility scripts
│   ├── build-image.sh      # Build bootable USB image
│   ├── build-whisper-cpp.sh # Compile whisper.cpp
│   └── download-models.sh  # Download Whisper models
├── models/                 # Pre-loaded Whisper models (GGML format)
├── benchmark/              # Benchmark audio samples
├── assets/                 # Icons, splash screen
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
