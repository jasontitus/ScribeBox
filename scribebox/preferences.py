"""Preferences management - persists settings to USB drive."""

import json
import os
from pathlib import Path
from typing import Any

# Default paths - on the USB image these live on a persistent data partition
DEFAULT_DATA_DIR = "/data/scribebox"
FALLBACK_DATA_DIR = os.path.expanduser("~/.local/share/scribebox")

DEFAULTS = {
    "model": "auto",
    "theme": "dark",
    "font_size": 24,
    "layout": "split",       # "full", "split", "three-panel"
    "diarization": False,
    "auto_save_interval": 60, # seconds
    "language": "en",
    "summary_window": 120,    # seconds for rolling summary
    "show_timestamps": True,
    "high_contrast": False,
    "transcript_font": "monospace",
}

# Available models in order of size
AVAILABLE_MODELS = [
    {"id": "tiny.en",    "name": "Tiny (English)",    "size_mb": 75,   "ram_mb": 390},
    {"id": "tiny",       "name": "Tiny (Multilingual)","size_mb": 75,   "ram_mb": 390},
    {"id": "base.en",    "name": "Base (English)",     "size_mb": 142,  "ram_mb": 500},
    {"id": "base",       "name": "Base (Multilingual)","size_mb": 142,  "ram_mb": 500},
    {"id": "small.en",   "name": "Small (English)",    "size_mb": 466,  "ram_mb": 1000},
    {"id": "small",      "name": "Small (Multilingual)","size_mb": 466, "ram_mb": 1000},
    {"id": "small.en-q5","name": "Small (English, Q5)", "size_mb": 190, "ram_mb": 600},
    {"id": "medium.en",  "name": "Medium (English)",    "size_mb": 1500,"ram_mb": 2600},
    {"id": "medium",     "name": "Medium (Multilingual)","size_mb":1500,"ram_mb": 2600},
    {"id": "medium.en-q5","name":"Medium (English, Q5)", "size_mb": 540,"ram_mb": 1400},
    {"id": "large-v3",   "name": "Large v3",              "size_mb": 3100,"ram_mb": 4700},
    {"id": "large-v3-turbo", "name": "Large v3 Turbo (Best)", "size_mb": 1600, "ram_mb": 3000},
    {"id": "large-v3-turbo-q5_0", "name": "Large v3 Turbo (Q5)", "size_mb": 600, "ram_mb": 1800},
]


class Preferences:
    """Load, save, and access user preferences."""

    def __init__(self, data_dir: str | None = None):
        self._data_dir = self._resolve_data_dir(data_dir)
        self._prefs_file = os.path.join(self._data_dir, "preferences.json")
        self._transcripts_dir = os.path.join(self._data_dir, "transcripts")
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    def _resolve_data_dir(self, data_dir: str | None) -> str:
        if data_dir:
            d = data_dir
        elif os.path.isdir(DEFAULT_DATA_DIR) and os.access(DEFAULT_DATA_DIR, os.W_OK):
            d = DEFAULT_DATA_DIR
        else:
            d = FALLBACK_DATA_DIR
        os.makedirs(d, exist_ok=True)
        return d

    def _load(self):
        if os.path.exists(self._prefs_file):
            try:
                with open(self._prefs_file, "r") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                pass  # Use defaults on corrupt file

    def save(self):
        os.makedirs(os.path.dirname(self._prefs_file), exist_ok=True)
        with open(self._prefs_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str) -> Any:
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any):
        self._data[key] = value

    @property
    def data_dir(self) -> str:
        return self._data_dir

    @property
    def transcripts_dir(self) -> str:
        os.makedirs(self._transcripts_dir, exist_ok=True)
        return self._transcripts_dir

    @property
    def model_id(self) -> str:
        return self._data.get("model", "auto")

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)
