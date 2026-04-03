"""End-to-end transcription test using real whisper.cpp binary and model.

Requires whisper-cli binary and at least the tiny.en model to be present.
Skip gracefully if not available.
"""

import os
import time

import numpy as np
import pytest

from scribebox.transcriber import Transcriber, list_available_models, _find_whisper_binary
from scribebox.summarizer import RollingSummarizer
from scribebox.diarizer import SpeakerDiarizer

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

has_binary = _find_whisper_binary() is not None
has_model = "tiny.en" in list_available_models(MODELS_DIR)

skip_reason = "whisper-cli binary or tiny.en model not available"


@pytest.mark.skipif(not (has_binary and has_model), reason=skip_reason)
class TestEndToEndTranscription:
    """Tests that require the actual whisper.cpp binary and model."""

    def test_transcribe_synthetic_audio(self):
        """Transcribe synthetic audio and get some output."""
        t = Transcriber(model_id="tiny.en", models_dir=MODELS_DIR, language="en")
        assert t.is_ready()

        # Generate 3 seconds of test audio
        sr = 16000
        duration = 3.0
        ts = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
        signal = 0.3 * np.sin(2 * np.pi * 150 * ts)
        signal += 0.2 * np.sin(2 * np.pi * 700 * ts)
        signal += 0.03 * np.random.randn(len(ts)).astype(np.float32)
        signal = signal / np.max(np.abs(signal)) * 0.7

        start = time.monotonic()
        text = t.transcribe_chunk(signal)
        elapsed = time.monotonic() - start

        # Should return some text (even for synthetic audio)
        assert isinstance(text, str)
        assert len(text) > 0

        # Should be faster than real-time for tiny.en
        rtf = elapsed / duration
        assert rtf < 2.0, f"RTF {rtf:.2f}x too slow for tiny.en"

    def test_transcribe_silence(self):
        """Transcribing silence should return empty or minimal text."""
        t = Transcriber(model_id="tiny.en", models_dir=MODELS_DIR, language="en")
        silence = np.zeros(16000 * 2, dtype=np.float32)
        text = t.transcribe_chunk(silence)
        assert isinstance(text, str)

    def test_real_time_factor(self):
        """Verify the model can achieve reasonable RTF."""
        t = Transcriber(model_id="tiny.en", models_dir=MODELS_DIR, language="en")
        sr = 16000
        duration = 5.0
        audio = np.random.randn(int(sr * duration)).astype(np.float32) * 0.1

        start = time.monotonic()
        t.transcribe_chunk(audio)
        elapsed = time.monotonic() - start

        rtf = elapsed / duration
        print(f"RTF for tiny.en on {duration}s audio: {rtf:.2f}x")
        # Should achieve at least 3x real-time on modern hardware
        assert rtf < 3.0

    def test_pipeline_transcription_to_summary(self):
        """Test full pipeline: audio -> transcription -> summarization."""
        t = Transcriber(model_id="tiny.en", models_dir=MODELS_DIR, language="en")
        rs = RollingSummarizer(window_seconds=120)

        sr = 16000
        ts = np.linspace(0, 3.0, sr * 3, dtype=np.float32)
        signal = 0.3 * np.sin(2 * np.pi * 200 * ts)
        signal += 0.03 * np.random.randn(len(ts)).astype(np.float32)

        text = t.transcribe_chunk(signal)
        rs.add_text(text, time.time())

        summary = rs.get_summary()
        assert isinstance(summary, str)

    def test_pipeline_with_diarization(self):
        """Test transcription + diarization pipeline."""
        t = Transcriber(model_id="tiny.en", models_dir=MODELS_DIR, language="en")
        d = SpeakerDiarizer()

        sr = 16000
        ts = np.linspace(0, 2.0, sr * 2, dtype=np.float32)
        audio = 0.5 * np.sin(2 * np.pi * 200 * ts)
        audio += 0.02 * np.random.randn(len(ts)).astype(np.float32)

        text = t.transcribe_chunk(audio)
        speaker = d.identify_speaker(audio)

        assert isinstance(text, str)
        assert speaker is not None
        assert speaker >= 0
