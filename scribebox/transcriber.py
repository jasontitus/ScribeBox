"""Whisper.cpp integration for real-time transcription.

Uses the whisper.cpp shared library via ctypes for maximum compatibility
on minimal systems. Falls back to subprocess calling the whisper.cpp CLI.
"""

import os
import subprocess
import tempfile
import struct
import time
import threading
from pathlib import Path

import numpy as np


def _find_models_dir(models_dir: str | None) -> str:
    """Locate the models directory."""
    candidates = [
        models_dir,
        os.environ.get("SCRIBEBOX_MODELS_DIR"),
        "/opt/scribebox/models",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "models"),
        os.path.expanduser("~/.local/share/scribebox/models"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


def _find_whisper_binary() -> str | None:
    """Find the whisper.cpp CLI binary."""
    candidates = [
        "/opt/scribebox/bin/whisper-cli",
        "/usr/local/bin/whisper-cli",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "bin", "whisper-cli"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    # Try PATH
    try:
        result = subprocess.run(["which", "whisper-cli"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def get_model_path(model_id: str, models_dir: str | None = None) -> str | None:
    """Get path to a GGML model file."""
    mdir = _find_models_dir(models_dir)
    # Try standard naming patterns
    patterns = [
        f"ggml-{model_id}.bin",
        f"ggml-{model_id.replace('-q5', '-q5_1')}.bin",
        f"whisper-{model_id}.bin",
    ]
    for pat in patterns:
        path = os.path.join(mdir, pat)
        if os.path.isfile(path):
            return path
    return None


def list_available_models(models_dir: str | None = None) -> list[str]:
    """List model IDs that have files on disk."""
    mdir = _find_models_dir(models_dir)
    if not os.path.isdir(mdir):
        return []
    models = []
    for f in os.listdir(mdir):
        if f.startswith("ggml-") and f.endswith(".bin"):
            model_id = f[5:-4]  # strip "ggml-" and ".bin"
            models.append(model_id)
    return sorted(models)


def _write_wav(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Create a WAV file in memory from float32 audio."""
    # Convert to int16
    pcm = (audio * 32767).astype(np.int16)
    data = pcm.tobytes()
    # WAV header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        1,  # mono
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        len(data),
    )
    return header + data


class Transcriber:
    """Real-time transcription using whisper.cpp CLI."""

    def __init__(self, model_id: str = "tiny.en", models_dir: str | None = None,
                 language: str = "en", threads: int | None = None):
        self._model_id = model_id
        self._models_dir = _find_models_dir(models_dir)
        self._language = language
        self._threads = threads or self._detect_threads()
        self._binary = _find_whisper_binary()
        self._model_path = get_model_path(model_id, self._models_dir)

    @staticmethod
    def _detect_threads() -> int:
        """Detect optimal thread count (physical cores)."""
        try:
            count = len(os.sched_getaffinity(0))
            return max(1, count)
        except AttributeError:
            return 2

    def is_ready(self) -> bool:
        """Check if model and binary are available."""
        return self._binary is not None and self._model_path is not None

    def transcribe_chunk(self, audio: np.ndarray) -> str:
        """Transcribe a numpy float32 audio chunk.

        Uses whisper.cpp CLI with a temp WAV file.
        Returns the transcribed text.
        """
        if not self.is_ready():
            return "[Model or whisper binary not found]"

        wav_data = _write_wav(audio)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            wav_path = f.name

        try:
            cmd = [
                self._binary,
                "-m", self._model_path,
                "-f", wav_path,
                "-t", str(self._threads),
                "-l", self._language,
                "--no-timestamps",
                "-np",  # no prints (only output transcription)
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                text = result.stdout.strip()
                # Clean up whisper output artifacts
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                return " ".join(lines)
            return ""
        except subprocess.TimeoutExpired:
            return "[Transcription timeout - try a smaller model]"
        except Exception:
            return ""
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    def change_model(self, model_id: str):
        """Switch to a different model."""
        self._model_id = model_id
        self._model_path = get_model_path(model_id, self._models_dir)

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def model_path(self) -> str | None:
        return self._model_path


class StreamingTranscriber:
    """Wraps Transcriber for continuous streaming from AudioCapture."""

    def __init__(self, transcriber: Transcriber, on_text=None, on_error=None):
        self._transcriber = transcriber
        self._on_text = on_text  # callback(text: str)
        self._on_error = on_error  # callback(error: str)
        self._running = False
        self._thread = None

    def start(self, audio_capture):
        """Start transcription loop in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(audio_capture,), daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self, audio_capture):
        """Main transcription loop."""
        # Buffer for accumulating audio for better context
        audio_buffer = np.array([], dtype=np.float32)
        buffer_max = 16000 * 10  # 10 seconds max buffer

        while self._running:
            chunk = audio_capture.get_chunk(timeout=2.0)
            if chunk is None:
                continue

            audio_buffer = np.concatenate([audio_buffer, chunk])

            # Transcribe when we have enough audio (at least 2 seconds)
            if len(audio_buffer) >= 16000 * 2:
                # Trim to max buffer size
                if len(audio_buffer) > buffer_max:
                    audio_buffer = audio_buffer[-buffer_max:]

                try:
                    text = self._transcriber.transcribe_chunk(audio_buffer)
                    if text and self._on_text:
                        self._on_text(text)
                    # Keep last 2 seconds for context overlap
                    audio_buffer = audio_buffer[-16000 * 2:]
                except Exception as e:
                    if self._on_error:
                        self._on_error(str(e))
