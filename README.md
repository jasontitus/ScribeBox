# ScribeBox

**A USB stick that turns any old laptop into a live transcription device.**

Plug it in. Reboot. Start transcribing. No internet, no setup, no accounts.

ScribeBox is a complete bootable operating system on a USB drive. It includes
everything needed to capture speech from a microphone and display it as text
in real time — with a rolling summary of what's been said and automatic
speaker detection.

---

## What Does It Do?

When you boot a computer from the ScribeBox USB stick:

1. The screen shows a large, easy-to-read transcription area
2. Press **F5** (or click "Start Recording") and speak into the microphone
3. Your words appear on screen as you speak
4. A summary of the last 2 minutes appears at the bottom
5. Different speakers are labeled automatically
6. Everything is saved to the USB stick

No internet connection needed. No cloud. No accounts. Everything runs locally
on the computer's own CPU.

## Who Is This For?

- **Meeting notes** — plug into a conference room laptop and transcribe the discussion
- **Lectures** — turn an old laptop into a captioning device for a classroom
- **Accessibility** — real-time captions for anyone who needs them
- **Interviews** — automatic transcription with speaker labels
- **Repurposing old hardware** — give a 2012 laptop a useful second life

## Will It Work on My Computer?

ScribeBox works on most **Intel/AMD laptops from 2011 or newer**:

| Your Computer | Works? | Transcription Quality |
|---------------|--------|----------------------|
| Laptop from 2015+ with 4-8 GB RAM | Great | High quality, real-time |
| Laptop from 2013-2014 with 4 GB RAM | Good | Good quality, real-time |
| Laptop from 2011-2012 with 2 GB RAM | OK | Basic quality, slight delay |
| Laptop before 2010 | Probably not | Too slow for live use |
| MacBook Pro 2013 or newer | Great | See above by RAM |
| MacBook Pro 2011-2012 | OK | Basic quality |
| MacBook with Apple Silicon (M1/M2/M3) | No | ARM — needs different build |
| Desktop PC (any era with 4+ GB RAM) | Great | Depends on CPU age |
| Chromebook | Maybe | Only if it can boot from USB |
| Tablet / iPad | No | Cannot boot from USB |

**What you need:**
- A computer that can boot from USB (almost all laptops can)
- A **16 GB or larger USB stick** (USB 3.0 recommended for speed)
- A working microphone (built-in laptop mic is fine)

## Quick Start

**There are three steps: build the USB, flash it, boot it.**

### Step 1: Build the Image

You need another computer (Mac, Linux, or Windows) to create the USB image.
This is a one-time process.

See **[BUILD.md](BUILD.md)** for detailed step-by-step instructions for your
platform. The short version:

```bash
git clone https://github.com/jasontitus/ScribeBox.git
cd ScribeBox
./build.sh
```

This downloads the AI models (~3.4 GB), compiles the transcription engine,
and creates a bootable disk image. Takes 10-30 minutes depending on your
internet speed and computer.

### Step 2: Flash to USB

The build produces a file called `build/scribebox.img`. You need to write
this to a USB stick. **This will erase everything on the USB stick.**

**Easiest method (any platform):**
Download [Balena Etcher](https://etcher.balena.io) (free), select the
`scribebox.img` file, select your USB stick, click Flash.

**Command line methods:** see [BUILD.md](BUILD.md).

### Step 3: Boot and Use

1. Plug the USB stick into the target computer
2. Reboot the computer
3. Enter the boot menu (usually **F12**, **F2**, **Esc**, or **Del** during startup — varies by manufacturer)
4. Select the USB stick from the boot menu
5. ScribeBox loads automatically

See **[USAGE.md](USAGE.md)** for the full user guide.

## What's Included on the USB

| Component | What It Does |
|-----------|-------------|
| 7 Whisper AI models (3.4 GB) | Speech-to-text, ranging from fast/basic to slower/best quality |
| whisper.cpp engine | Runs the AI models efficiently on your CPU, no GPU needed |
| ScribeBox application | The transcription UI, summarizer, and settings |
| Minimal Linux OS | Just enough operating system to boot and run ScribeBox |
| Benchmark tool | Tests your hardware to pick the best model |

### The AI Models

ScribeBox ships with 7 models. The benchmark tool tests your hardware and
picks the best one automatically, or you can choose manually in Preferences.

| Model | Size | RAM Needed | Speed vs Quality |
|-------|------|-----------|------------------|
| tiny.en | 75 MB | 1 GB | Fastest, basic quality. Good for old/slow machines. |
| base.en | 142 MB | 1.5 GB | Fast, good quality. Sweet spot for most old laptops. |
| small.en (quantized) | 182 MB | 1.5 GB | Moderate speed, better quality. Compressed to save RAM. |
| small.en | 466 MB | 2.5 GB | Good speed, great quality. Best for 4-8 GB machines. |
| medium.en (quantized) | 515 MB | 3 GB | Slower, very good quality. Needs 8+ GB RAM. |
| large-v3-turbo (quantized) | 548 MB | 4 GB | Slow, excellent quality. Needs modern CPU + 8 GB. |
| large-v3-turbo | 1.6 GB | 6 GB | Slowest, best possible quality. Needs fast modern CPU. |

"Quantized" means the model has been compressed to use less memory, with
minimal quality loss. The "(en)" models are English-only and perform better
for English than the multilingual versions.

## Customizing ScribeBox

All settings are accessible from the **Preferences** button (or press **F2**):

- **Theme**: Dark (default), Light, or High Contrast
- **Font size**: 14pt to 48pt — make it readable from across the room
- **Layout**: Full transcript, or split view with summary below
- **AI Model**: Auto (recommended), or manually select
- **Speaker detection**: On/off
- **Language**: English (default) or auto-detect
- **Auto-save**: How often to save transcripts (default: every 60 seconds)

Settings are saved on the USB stick and persist between reboots.

## For Developers

Want to modify ScribeBox or understand how it works?

- **[BUILD.md](BUILD.md)** — How to build the USB image (detailed, all platforms)
- **[USAGE.md](USAGE.md)** — User guide for the transcription appliance
- **[HACKING.md](HACKING.md)** — Developer guide: architecture, how to modify components, add features

### Project Structure

```
ScribeBox/
├── build.sh                    # One-command build (start here)
├── scribebox/                  # Python application
│   ├── app.py                  # Main controller
│   ├── transcriber.py          # whisper.cpp integration
│   ├── audio.py                # Microphone capture
│   ├── summarizer.py           # TextRank summarization
│   ├── diarizer.py             # Speaker identification (MFCC)
│   ├── benchmark.py            # Hardware speed testing
│   ├── preferences.py          # Settings management
│   └── ui/                     # GTK3 interface
├── scripts/                    # Build scripts
├── configs/                    # Linux boot configuration
├── docker/                     # Docker build environment
├── tests/                      # 70 automated tests
└── models/                     # AI model files (3.4 GB)
```

### Running Tests

```bash
# Create a Python 3.12 virtual environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install numpy scipy PyYAML pytest sounddevice PyGObject

# Run all 70 tests
pytest tests/ -v
```

## License

MIT — free to use, modify, and distribute.
