# Hacking on ScribeBox

This guide is for developers who want to understand, modify, or extend
ScribeBox. It covers the architecture, how each component works, how to
develop without building a full USB image, and how to add new features.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Development Setup](#development-setup)
- [How the Components Work](#how-the-components-work)
- [The Boot Process](#the-boot-process)
- [Common Modifications](#common-modifications)
- [Testing](#testing)
- [Adding a New Feature](#adding-a-new-feature)
- [Technical Decisions and Trade-offs](#technical-decisions-and-trade-offs)

---

## Architecture Overview

ScribeBox is a pipeline:

```
Microphone → Audio Capture → Whisper Transcription → Display
                                      ↓
                              Text Accumulator
                              ↓              ↓
                         Summarizer     Diarizer
                              ↓              ↓
                         Summary Panel   Speaker Labels
```

**Key design constraints:**
- Must run on 2010-2015 era laptops (2-4 GB RAM, dual-core CPU)
- No internet required — everything runs locally
- No GPU required — CPU-only inference via whisper.cpp
- Minimal dependencies — boots from USB in seconds

**Technology choices:**
| Component | Technology | Why |
|-----------|-----------|-----|
| OS | Debian Bookworm (minimal) | Stable, broad hardware support, small |
| Display server | X.org with modesetting | Works with any GPU from the last 15 years |
| UI toolkit | GTK 3 + Python | Pre-installed on Debian, no compilation needed |
| Speech-to-text | whisper.cpp (C++) | 5-10x faster than Python Whisper on CPU |
| Summarization | TextRank (pure Python) | Zero-dependency, instant, <50 MB RAM |
| Speaker ID | MFCC + Euclidean clustering | No model download, ~1 MB RAM |
| Audio capture | sounddevice (PortAudio) | Cross-platform, simple API |
| Settings | JSON file | Human-readable, no database needed |

---

## Development Setup

You can develop and test ScribeBox on your normal computer without building
a USB image.

### Prerequisites

```bash
# Python 3.12 (3.10+ should work)
# GTK 3 development libraries
# A C++ compiler (for whisper.cpp)

# Ubuntu/Debian
sudo apt install python3.12-dev python3.12-venv libgirepository-2.0-dev \
    libcairo2-dev pkg-config cmake build-essential

# Mac
brew install python@3.12 pygobject3 gtk+3 cmake
```

### Setup

```bash
# Clone the repo
git clone https://github.com/jasontitus/ScribeBox.git
cd ScribeBox

# Create a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install numpy scipy PyYAML pytest sounddevice PyGObject

# Build whisper.cpp (compiles the C++ binary)
./scripts/build-whisper-cpp.sh

# Download at least one model (tiny.en is 75 MB)
mkdir -p models
curl -L -o models/ggml-tiny.en.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin

# Run ScribeBox
python -m scribebox --models-dir models --data-dir /tmp/scribebox-dev
```

### Running Without a Microphone

If you're developing on a machine without a mic (e.g., a server or VM),
the app will start but recording won't work. You can still test:

- The UI (themes, layout, preferences dialog)
- The benchmark tool: `python -m scribebox --benchmark --models-dir models`
- Individual modules in Python or via the test suite

---

## How the Components Work

### `scribebox/audio.py` — Audio Capture

Captures 16kHz mono audio from the default input device using the `sounddevice`
library (which wraps PortAudio).

**How it works:**
1. Opens an audio input stream via `sounddevice.InputStream`
2. A callback function receives small blocks of audio (~100ms each)
3. The callback accumulates audio in a buffer
4. When the buffer reaches the chunk size (default: 2 seconds), it's placed
   on a thread-safe queue
5. The transcription thread consumes chunks from this queue

**Key parameters:**
- `SAMPLE_RATE = 16000` — Whisper expects 16kHz audio
- `CHANNELS = 1` — Mono (Whisper is mono-only)
- `CHUNK_DURATION = 2.0` — Seconds per chunk sent to Whisper
- Queue max size: 30 chunks — if the consumer falls behind, old chunks are dropped

**To modify:** Change `CHUNK_DURATION` to trade latency vs accuracy. Shorter
chunks = lower latency but Whisper has less context. Longer = better accuracy
but more delay before text appears.

### `scribebox/transcriber.py` — Whisper Integration

Bridges between Python and the whisper.cpp C++ binary.

**How it works:**
1. Audio chunks (numpy float32 arrays) come in from the audio capture
2. Each chunk is converted to a WAV file in `/tmp/`
3. The `whisper-cli` binary is called as a subprocess
4. stdout is captured and cleaned up (strip blank lines, artifacts)
5. The temp WAV file is deleted

**Why subprocess instead of Python bindings?**
- whisper.cpp Python bindings (whispercpp) are fragile and version-sensitive
- The CLI binary is statically linked and always works
- Subprocess overhead is negligible vs inference time (~1ms vs ~500ms+)

**Key classes:**
- `Transcriber` — synchronous, transcribes one chunk at a time
- `StreamingTranscriber` — wraps Transcriber in a background thread,
  calls a callback with each new text segment

**The audio buffer in StreamingTranscriber:**
The streamer maintains a sliding window of audio (up to 10 seconds). Each
time it transcribes, it processes the full window but keeps the last 2 seconds
as overlap for the next transcription. This gives Whisper more context than
a single 2-second chunk, improving accuracy at sentence boundaries.

### `scribebox/summarizer.py` — Text Summarization

Pure Python extractive summarization using the TextRank algorithm. No model
download needed, runs instantly, uses negligible RAM.

**How TextRank works:**
1. Split the transcript into sentences
2. Build a graph where each sentence is a node
3. Edges between nodes are weighted by word overlap (similarity)
4. Run a PageRank-like algorithm to score each sentence
5. Pick the top N sentences (preserving original order)

**Why not a neural summarizer?**
Neural summarizers (BART, T5, etc.) produce better summaries but:
- Need 300MB-2GB of RAM for the model
- Take 5-30 seconds per summary on old CPUs
- Compete with Whisper for CPU time

TextRank is free: zero RAM, instant results, and "good enough" for a
rolling 2-minute window of transcript text.

**`RollingSummarizer` class:**
Maintains a time-windowed buffer of transcript segments. When asked for a
summary, it concatenates all text in the window and runs TextRank.
The window automatically prunes segments older than `window_seconds`.

### `scribebox/diarizer.py` — Speaker Identification

Identifies which speaker is talking using acoustic features.

**How it works:**
1. **VAD (Voice Activity Detection):** Checks if the audio chunk contains
   speech by measuring RMS energy per frame. If less than 30% of frames
   have energy above the threshold, it's silence → return None.

2. **Feature extraction:** Computes 13 MFCCs (Mel-Frequency Cepstral
   Coefficients) from the audio. MFCCs capture the shape of the vocal
   tract, which differs between speakers. The implementation computes
   MFCCs from scratch (no external library needed): pre-emphasis →
   framing → Hamming window → FFT → mel filterbank → log → DCT.

3. **Speaker matching:** Compares the MFCC vector to stored speaker
   profiles using Euclidean distance. If the distance is below the
   threshold (15.0), it's the same speaker. Otherwise, it's a new speaker.

4. **Profile updating:** When a known speaker is re-identified, their
   profile is updated with an exponential moving average (alpha=0.1)
   to adapt to slight voice changes over time.

**Limitations:**
- Works best with 2-3 speakers
- Pure tone signals (not real speech) may not separate well
- No pre-trained model — clustering is unsupervised
- Speakers must be somewhat acoustically different

**To improve diarization:**
Replace `_extract_features()` with a proper speaker embedding model like
`resemblyzer` (17 MB, much more accurate). This would require adding
resemblyzer as a dependency and downloading its model. The interface
would stay the same — just return a different feature vector.

### `scribebox/benchmark.py` — Hardware Speed Testing

Tests each available model to determine real-time capability.

**How it works:**
1. Generate 5 seconds of synthetic audio (speech-like harmonics + noise)
2. Write it to a temp WAV file
3. For each model:
   a. Run whisper-cli once as a warmup (fills OS disk cache with model data)
   b. Run again and measure wall-clock time
   c. Compute RTF = time / audio_duration
4. Recommend the largest model with RTF < 1.0

**`auto_select_model()`:**
A fast heuristic (no inference, instant) that picks a model based solely
on available RAM. Used when preferences are set to "auto" so the app
starts immediately without running a full benchmark.

### `scribebox/preferences.py` — Settings

JSON-based preferences stored on the USB stick's data partition.

**Search order for data directory:**
1. `--data-dir` command line argument
2. `/data/scribebox` (the USB image's data partition)
3. `~/.local/share/scribebox` (fallback for development)

The file is simple JSON. If it's corrupt or missing, all settings fall
back to their defaults. New settings added in future versions are
automatically filled with defaults.

### `scribebox/ui/` — User Interface

GTK 3 interface with CSS-based theming.

**`theme.py`:** Defines three themes (dark, light, high_contrast) as dicts
of color values. `generate_css()` turns a theme dict into GTK CSS.

**`transcript_view.py`:** A `Gtk.ScrolledWindow` containing a `Gtk.TextView`.
Auto-scrolls to the bottom as new text arrives (unless the user has scrolled
up to review earlier text). Uses GTK text tags for speaker colors and
timestamps.

**`summary_panel.py`:** A `Gtk.Box` with a label, keyword tags, and a
scrollable text view for the summary.

**`main_window.py`:** Assembles the header bar, transcript view, summary
panel, and status bar into a `Gtk.Paned` layout.

**`preferences_dialog.py`:** A `Gtk.Dialog` with two tabs (Transcription
and Appearance) built from GTK widgets.

**Thread safety:** All UI updates go through `GLib.idle_add()` since
transcription runs in a background thread. Never call GTK methods directly
from non-main threads.

### `scribebox/app.py` — Main Controller

Wires everything together:
- Creates the window, transcriber, audio capture, summarizer, diarizer
- Handles button clicks and keyboard shortcuts
- Manages the recording lifecycle (start/stop/save)
- Runs periodic timers for summary updates and auto-save

---

## The Boot Process

When a computer boots from the ScribeBox USB:

```
BIOS/UEFI
  → GRUB bootloader (partition 1, FAT32)
    → Linux kernel + initramfs (partition 2, ext4)
      → systemd init
        → getty@tty1 with auto-login (scribebox user)
          → ~/.bash_profile runs startx
            → ~/.xinitrc starts ScribeBox
              → python3 -m scribebox (fullscreen)
```

**Partition layout:**
| # | Label | Format | Size | Contents |
|---|-------|--------|------|----------|
| 1 | SCRIBBOOT | FAT32 | 512 MB | GRUB bootloader, kernel |
| 2 | scribebox | ext4 | ~5.5 GB | Linux root filesystem, models, app |
| 3 | scribedata | ext4 | ~2 GB | Preferences, transcripts (persistent) |

**Key config files in the image:**
- `/etc/systemd/system/getty@tty1.service.d/autologin.conf` — auto-login
- `/home/scribebox/.bash_profile` — starts X on tty1
- `/home/scribebox/.xinitrc` — starts ScribeBox, disables screensaver
- `/etc/X11/xorg.conf` — modesetting driver, no screen blanking
- `/opt/scribebox/` — application code, models, whisper binary

---

## Common Modifications

### Change the default theme

Edit `scribebox/preferences.py`, change the `DEFAULTS` dict:
```python
DEFAULTS = {
    "theme": "high_contrast",  # was "dark"
    "font_size": 32,           # was 24
    ...
}
```

### Add a new theme

Edit `scribebox/ui/theme.py`, add to the `THEMES` dict:
```python
"solarized": {
    "name": "Solarized",
    "bg": "#002b36",
    "bg_secondary": "#073642",
    "text": "#839496",
    ...
}
```

Then add it to the combo box in `scribebox/ui/preferences_dialog.py`.

### Change the summarization algorithm

Replace the body of `textrank_summarize()` in `scribebox/summarizer.py`.
The function signature is:
```python
def textrank_summarize(text: str, num_sentences: int = 3) -> str:
```

For example, you could plug in the `sumy` library for LSA or LexRank,
or use a small transformer model via ONNX Runtime.

### Add a new Whisper model

1. Download the GGML model file to `models/`
2. Name it `ggml-{model_id}.bin`
3. Add an entry to `AVAILABLE_MODELS` in `scribebox/preferences.py`
4. Update `auto_select_model()` in `scribebox/benchmark.py` if needed

### Change the audio chunk size

In `scribebox/app.py`, the `_start_recording()` method creates the
AudioCapture with `chunk_duration=3.0`. Change this value:
- Lower (1-2s): Text appears faster, but less accurate per chunk
- Higher (5-10s): More accurate, but longer delay before text appears

### Export transcripts in different formats

Modify `_save_transcript()` in `scribebox/app.py`. Currently saves plain
text. You could add SRT subtitle format, JSON with timestamps, or CSV
with speaker labels.

### Add real-time translation

Chain a translation model after transcription. In `_on_transcription()`,
pass the text through a translation function before displaying. Small
translation models (like Helsinki-NLP OPUS models via CTranslate2) can
run on CPU with ~200 MB RAM.

---

## Testing

### Run all tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

### Test categories

| File | Tests | What | Needs whisper? |
|------|-------|------|---------------|
| `test_audio.py` | 6 | Audio capture, buffer chunking, queue overflow | No |
| `test_benchmark.py` | 6 | Test audio generation, system info, model auto-select | No |
| `test_diarizer.py` | 9 | VAD, MFCC extraction, speaker clustering | No |
| `test_preferences.py` | 9 | Settings load/save/defaults, corrupt file handling | No |
| `test_summarizer.py` | 11 | TextRank, sentence splitting, keywords, rolling window | No |
| `test_transcriber.py` | 7 | WAV generation, model discovery, error handling | No |
| `test_e2e_transcription.py` | 5 | Real whisper inference, pipeline integration | **Yes** |

The end-to-end tests are automatically skipped if whisper-cli or models
are not present.

### Test the GTK UI (headless)

```bash
sudo apt install xvfb
xvfb-run -a python3 -c "
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from scribebox.preferences import Preferences
from scribebox.ui.main_window import MainWindow

prefs = Preferences(data_dir='/tmp/scribebox-test')
win = MainWindow(prefs)
win.transcript_view.append_text('Hello world', speaker=0)
while Gtk.events_pending():
    Gtk.main_iteration_do(False)
print('UI test passed')
win.destroy()
"
```

### Add a new test

Follow the existing patterns in `tests/`. Key conventions:
- Use `tmp_path` (pytest fixture) for any file I/O
- End-to-end tests that need whisper should be in a class decorated with
  `@pytest.mark.skipif(not has_binary, ...)` so they skip gracefully in CI

---

## Technical Decisions and Trade-offs

### Why whisper.cpp subprocess instead of Python bindings?

Python bindings for whisper.cpp (the `whispercpp` PyPI package) are fragile:
version mismatches, compilation issues, different APIs across versions. The
CLI binary is a single static file that always works. The ~1ms subprocess
overhead is negligible next to 500ms+ inference time.

### Why GTK 3 instead of a web UI?

A web UI (Flask/Electron) would be more portable and easier to style, but:
- Electron alone is ~150 MB (too big for a minimal USB image)
- A Flask server + browser adds two processes and more RAM
- GTK 3 is pre-installed on Debian — zero extra bytes in the image
- GTK 3 starts instantly, no browser startup time

### Why TextRank instead of an LLM for summarization?

An LLM would produce much better summaries, but:
- The smallest useful LLMs (TinyLlama, Phi-2) need 1-4 GB RAM
- They'd compete with Whisper for CPU time
- Inference takes 5-30 seconds per summary on old hardware
- TextRank is instant, zero RAM, and "good enough" for rolling summaries

### Why custom MFCC implementation instead of librosa?

Librosa is listed in requirements.txt but the diarizer computes MFCCs from
scratch to avoid the heavy librosa import (~5 seconds on old hardware,
pulls in numba/llvmlite). The custom implementation is ~60 lines and
produces equivalent 13-dimensional MFCC vectors.

### Why Debian Bookworm?

- Stable release with long support window
- `debootstrap` makes minimal installs easy
- Excellent hardware support (drivers for old Intel/AMD/NVIDIA GPUs)
- Python 3.11 and GTK 3 packages available in base repos

### Why not Alpine Linux?

Alpine would make a smaller image (~100 MB vs ~2 GB for the OS), but:
- Uses musl instead of glibc — whisper.cpp and many Python packages
  need patches or don't work
- Smaller package ecosystem for audio/GPU drivers
- Less battle-tested on diverse hardware

### Why a 3-partition layout?

Partition 3 (data) is separate so the OS partition can be read-only in
future versions. This prevents corruption from unexpected power loss and
makes updates easier (replace partition 2, keep partition 3).
