"""Tests for the preferences module."""

import json
import os
import tempfile
import pytest

from scribebox.preferences import Preferences, DEFAULTS, AVAILABLE_MODELS


class TestPreferences:
    def test_defaults(self, tmp_path):
        prefs = Preferences(data_dir=str(tmp_path))
        for key, value in DEFAULTS.items():
            assert prefs.get(key) == value

    def test_set_and_get(self, tmp_path):
        prefs = Preferences(data_dir=str(tmp_path))
        prefs.set("font_size", 36)
        assert prefs.get("font_size") == 36

    def test_save_and_reload(self, tmp_path):
        prefs = Preferences(data_dir=str(tmp_path))
        prefs.set("theme", "light")
        prefs.set("font_size", 32)
        prefs.set("diarization", True)
        prefs.save()

        # Reload from disk
        prefs2 = Preferences(data_dir=str(tmp_path))
        assert prefs2.get("theme") == "light"
        assert prefs2.get("font_size") == 32
        assert prefs2.get("diarization") is True
        # Unchanged defaults still present
        assert prefs2.get("layout") == "split"

    def test_corrupt_file_falls_back_to_defaults(self, tmp_path):
        prefs_file = tmp_path / "preferences.json"
        prefs_file.write_text("{invalid json!!!}")
        prefs = Preferences(data_dir=str(tmp_path))
        assert prefs.get("theme") == "dark"

    def test_data_dir_creation(self, tmp_path):
        new_dir = tmp_path / "subdir" / "deep"
        prefs = Preferences(data_dir=str(new_dir))
        assert os.path.isdir(str(new_dir))

    def test_transcripts_dir(self, tmp_path):
        prefs = Preferences(data_dir=str(tmp_path))
        tdir = prefs.transcripts_dir
        assert os.path.isdir(tdir)
        assert tdir.endswith("transcripts")

    def test_get_all(self, tmp_path):
        prefs = Preferences(data_dir=str(tmp_path))
        prefs.set("model", "base.en")
        all_prefs = prefs.get_all()
        assert isinstance(all_prefs, dict)
        assert all_prefs["model"] == "base.en"
        assert "font_size" in all_prefs

    def test_model_id_property(self, tmp_path):
        prefs = Preferences(data_dir=str(tmp_path))
        assert prefs.model_id == "auto"
        prefs.set("model", "tiny.en")
        assert prefs.model_id == "tiny.en"

    def test_available_models_structure(self):
        assert len(AVAILABLE_MODELS) > 0
        for m in AVAILABLE_MODELS:
            assert "id" in m
            assert "name" in m
            assert "size_mb" in m
            assert "ram_mb" in m
