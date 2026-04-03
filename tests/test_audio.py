"""Tests for the audio module."""

import numpy as np
import pytest

from scribebox.audio import AudioCapture


class TestAudioCapture:
    def test_constants(self):
        assert AudioCapture.SAMPLE_RATE == 16000
        assert AudioCapture.CHANNELS == 1

    def test_initialization(self):
        ac = AudioCapture(chunk_duration=2.0)
        assert ac._chunk_samples == 32000
        assert not ac.is_running

    def test_custom_chunk_duration(self):
        ac = AudioCapture(chunk_duration=5.0)
        assert ac._chunk_samples == 80000

    def test_get_chunk_timeout(self):
        ac = AudioCapture()
        # Should return None on timeout (no audio stream running)
        result = ac.get_chunk(timeout=0.1)
        assert result is None

    def test_internal_buffer_chunking(self):
        """Test that the callback correctly chunks audio."""
        ac = AudioCapture(chunk_duration=1.0)  # 16000 samples per chunk

        # Simulate feeding audio via the callback
        fake_audio = np.random.randn(24000).astype(np.float32).reshape(-1, 1)
        ac._audio_callback(fake_audio, 24000, None, None)

        # Should have one complete chunk (16000 samples) in the queue
        chunk = ac.get_chunk(timeout=0.1)
        assert chunk is not None
        assert len(chunk) == 16000

        # 8000 samples remaining in buffer (not enough for a chunk)
        chunk2 = ac.get_chunk(timeout=0.1)
        assert chunk2 is None

    def test_queue_overflow_handling(self):
        """Test that old chunks are dropped when queue is full."""
        ac = AudioCapture(chunk_duration=0.1)  # small chunks = 1600 samples
        ac._queue.maxsize = 2

        # Feed enough audio for many chunks
        big_audio = np.random.randn(32000).astype(np.float32).reshape(-1, 1)
        ac._audio_callback(big_audio, 32000, None, None)

        # Queue should not be over capacity
        assert ac._queue.qsize() <= 2
