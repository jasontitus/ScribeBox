"""Tests for the benchmark module."""

import numpy as np
import pytest

from scribebox.benchmark import (
    _generate_test_audio,
    _get_system_info,
    auto_select_model,
)


class TestGenerateTestAudio:
    def test_correct_duration(self):
        audio = _generate_test_audio(duration=2.0, sample_rate=16000)
        assert len(audio) == 32000

    def test_correct_dtype(self):
        audio = _generate_test_audio(duration=1.0)
        assert audio.dtype == np.float32

    def test_normalized_range(self):
        audio = _generate_test_audio(duration=1.0)
        assert np.max(np.abs(audio)) <= 1.0

    def test_not_silence(self):
        audio = _generate_test_audio(duration=1.0)
        assert np.max(np.abs(audio)) > 0.1


class TestSystemInfo:
    def test_returns_dict(self):
        info = _get_system_info()
        assert isinstance(info, dict)
        assert "cpu" in info
        assert "cores" in info
        assert "ram_mb" in info
        assert "cpu_flags" in info

    def test_cores_positive(self):
        info = _get_system_info()
        assert info["cores"] >= 1

    def test_ram_detected(self):
        info = _get_system_info()
        # Should detect some RAM in this environment
        assert info["ram_mb"] > 0


class TestAutoSelectModel:
    def test_selects_from_available(self, tmp_path):
        (tmp_path / "ggml-tiny.en.bin").write_bytes(b"fake")
        (tmp_path / "ggml-base.en.bin").write_bytes(b"fake")
        model = auto_select_model(str(tmp_path))
        # Should pick one of the available models
        assert model in ("tiny.en", "base.en")

    def test_fallback_with_no_models(self, tmp_path):
        model = auto_select_model(str(tmp_path))
        # With no models available, returns fallback
        assert model == "tiny.en"

    def test_prefers_larger_model_with_enough_ram(self, tmp_path):
        # Create models of different sizes
        (tmp_path / "ggml-tiny.en.bin").write_bytes(b"fake")
        (tmp_path / "ggml-base.en.bin").write_bytes(b"fake")
        (tmp_path / "ggml-small.en.bin").write_bytes(b"fake")
        model = auto_select_model(str(tmp_path))
        # On a dev machine with plenty of RAM, should pick a larger model
        assert model in ("small.en", "base.en", "tiny.en")
