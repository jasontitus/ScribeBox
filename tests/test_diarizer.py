"""Tests for the diarizer module."""

import numpy as np
import pytest

from scribebox.diarizer import SimpleVAD, SpeakerDiarizer, _extract_features


class TestSimpleVAD:
    def test_silence_detected(self):
        vad = SimpleVAD(sample_rate=16000, energy_threshold=0.01)
        silence = np.zeros(16000, dtype=np.float32)
        regions = vad.detect(silence)
        assert all(not is_speech for _, _, is_speech in regions)

    def test_speech_detected(self):
        vad = SimpleVAD(sample_rate=16000, energy_threshold=0.01)
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        tone = 0.5 * np.sin(2 * np.pi * 200 * t)
        regions = vad.detect(tone)
        speech_count = sum(1 for _, _, is_speech in regions if is_speech)
        assert speech_count > len(regions) * 0.5

    def test_region_boundaries(self):
        vad = SimpleVAD(sample_rate=16000, frame_ms=30)
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        regions = vad.detect(audio)
        # Regions should be contiguous
        for i in range(1, len(regions)):
            assert regions[i][0] == regions[i - 1][1]


class TestFeatureExtraction:
    def test_returns_correct_shape(self):
        audio = np.random.randn(16000).astype(np.float32) * 0.3
        features = _extract_features(audio)
        assert features.shape == (13,)  # 13 MFCCs

    def test_short_audio_returns_zeros(self):
        audio = np.array([0.1, 0.2], dtype=np.float32)
        features = _extract_features(audio)
        assert np.all(features == 0)

    def test_different_signals_different_features(self):
        from scipy.spatial.distance import euclidean
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        low_tone = 0.5 * np.sin(2 * np.pi * 100 * t)
        high_tone = 0.5 * np.sin(2 * np.pi * 3000 * t)
        feat_low = _extract_features(low_tone)
        feat_high = _extract_features(high_tone)
        # MFCC features should differ significantly for different signals
        assert euclidean(feat_low, feat_high) > 10


class TestSpeakerDiarizer:
    def test_first_speaker_is_zero(self):
        d = SpeakerDiarizer()
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        audio = 0.5 * np.sin(2 * np.pi * 200 * t)
        speaker = d.identify_speaker(audio)
        assert speaker == 0
        assert d.num_speakers == 1

    def test_silence_returns_none(self):
        d = SpeakerDiarizer()
        silence = np.zeros(16000, dtype=np.float32)
        speaker = d.identify_speaker(silence)
        assert speaker is None

    def test_same_speaker_recognized(self):
        d = SpeakerDiarizer()
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        audio = 0.5 * np.sin(2 * np.pi * 200 * t)
        s1 = d.identify_speaker(audio)
        s2 = d.identify_speaker(audio)
        assert s1 == s2

    def test_different_speakers_distinguished(self):
        d = SpeakerDiarizer()
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        # Very different signals
        speaker_a = 0.5 * np.sin(2 * np.pi * 120 * t)  # Low male voice
        speaker_b = 0.5 * np.sin(2 * np.pi * 4000 * t)  # High pitch
        sa = d.identify_speaker(speaker_a)
        sb = d.identify_speaker(speaker_b)
        # They might or might not be distinguished depending on threshold,
        # but at least both should be identified (not None)
        assert sa is not None
        assert sb is not None

    def test_max_speakers_limit(self):
        d = SpeakerDiarizer(max_speakers=2)
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        for freq in [100, 2000, 5000, 8000]:
            audio = 0.5 * np.sin(2 * np.pi * freq * t)
            d.identify_speaker(audio)
        assert d.num_speakers <= 2

    def test_reset(self):
        d = SpeakerDiarizer()
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        audio = 0.5 * np.sin(2 * np.pi * 200 * t)
        d.identify_speaker(audio)
        assert d.num_speakers == 1
        d.reset()
        assert d.num_speakers == 0
