"""Tests for the transcriber module."""

import os
import struct
import tempfile

import numpy as np
import pytest

from scribebox.transcriber import (
    _write_wav,
    get_model_path,
    list_available_models,
    Transcriber,
)


class TestWriteWav:
    def test_valid_wav_header(self):
        audio = np.zeros(16000, dtype=np.float32)
        wav_data = _write_wav(audio, sample_rate=16000)
        assert wav_data[:4] == b"RIFF"
        assert wav_data[8:12] == b"WAVE"
        assert wav_data[12:16] == b"fmt "
        assert wav_data[36:40] == b"data"

    def test_correct_data_size(self):
        samples = 16000  # 1 second at 16kHz
        audio = np.zeros(samples, dtype=np.float32)
        wav_data = _write_wav(audio, sample_rate=16000)
        # Data chunk size should be samples * 2 (int16)
        data_size = struct.unpack_from("<I", wav_data, 40)[0]
        assert data_size == samples * 2

    def test_correct_sample_rate(self):
        audio = np.zeros(16000, dtype=np.float32)
        wav_data = _write_wav(audio, sample_rate=16000)
        sr = struct.unpack_from("<I", wav_data, 24)[0]
        assert sr == 16000

    def test_mono_channel(self):
        audio = np.zeros(16000, dtype=np.float32)
        wav_data = _write_wav(audio, sample_rate=16000)
        channels = struct.unpack_from("<H", wav_data, 22)[0]
        assert channels == 1


class TestModelDiscovery:
    def test_list_empty_dir(self, tmp_path):
        models = list_available_models(str(tmp_path))
        assert models == []

    def test_list_finds_models(self, tmp_path):
        (tmp_path / "ggml-tiny.en.bin").write_bytes(b"fake")
        (tmp_path / "ggml-base.en.bin").write_bytes(b"fake")
        (tmp_path / "not-a-model.txt").write_bytes(b"fake")
        models = list_available_models(str(tmp_path))
        assert "tiny.en" in models
        assert "base.en" in models
        assert len(models) == 2

    def test_get_model_path_exists(self, tmp_path):
        (tmp_path / "ggml-tiny.en.bin").write_bytes(b"fake")
        path = get_model_path("tiny.en", str(tmp_path))
        assert path is not None
        assert path.endswith("ggml-tiny.en.bin")

    def test_get_model_path_missing(self, tmp_path):
        path = get_model_path("large-v3", str(tmp_path))
        assert path is None


class TestTranscriber:
    def test_not_ready_without_binary(self, tmp_path):
        t = Transcriber(model_id="tiny.en", models_dir=str(tmp_path))
        assert not t.is_ready()

    def test_transcribe_returns_message_when_not_ready(self, tmp_path):
        t = Transcriber(model_id="tiny.en", models_dir=str(tmp_path))
        audio = np.zeros(16000, dtype=np.float32)
        result = t.transcribe_chunk(audio)
        assert "not found" in result.lower()

    def test_change_model(self, tmp_path):
        (tmp_path / "ggml-tiny.en.bin").write_bytes(b"fake")
        (tmp_path / "ggml-base.en.bin").write_bytes(b"fake")
        t = Transcriber(model_id="tiny.en", models_dir=str(tmp_path))
        assert t.model_id == "tiny.en"
        t.change_model("base.en")
        assert t.model_id == "base.en"
        assert t.model_path.endswith("ggml-base.en.bin")
