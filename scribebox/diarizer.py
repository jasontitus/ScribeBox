"""Lightweight speaker diarization using VAD and spectral clustering.

Designed for 2-speaker scenarios on old hardware.
Uses WebRTC VAD for speech detection and simple acoustic features for clustering.
"""

import numpy as np
from scipy.spatial.distance import cosine


class SimpleVAD:
    """Voice Activity Detection using energy and zero-crossing rate."""

    def __init__(self, sample_rate: int = 16000, frame_ms: int = 30,
                 energy_threshold: float = 0.01):
        self._sample_rate = sample_rate
        self._frame_size = int(sample_rate * frame_ms / 1000)
        self._energy_threshold = energy_threshold

    def detect(self, audio: np.ndarray) -> list[tuple[int, int, bool]]:
        """Detect speech regions.

        Returns list of (start_sample, end_sample, is_speech).
        """
        regions = []
        for i in range(0, len(audio) - self._frame_size, self._frame_size):
            frame = audio[i:i + self._frame_size]
            energy = np.sqrt(np.mean(frame ** 2))
            is_speech = energy > self._energy_threshold
            regions.append((i, i + self._frame_size, is_speech))
        return regions


def _extract_features(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """Extract simple acoustic features for speaker identification.

    Returns a feature vector: [spectral_centroid, spectral_bandwidth, zcr, energy,
                               low_energy_ratio, spectral_rolloff]
    """
    if len(audio) < 512:
        return np.zeros(6)

    # Spectral features via FFT
    fft = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1.0 / sample_rate)

    # Spectral centroid
    if np.sum(fft) > 0:
        centroid = np.sum(freqs * fft) / np.sum(fft)
    else:
        centroid = 0.0

    # Spectral bandwidth
    if np.sum(fft) > 0:
        bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * fft) / np.sum(fft))
    else:
        bandwidth = 0.0

    # Zero crossing rate
    zcr = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))

    # RMS energy
    energy = np.sqrt(np.mean(audio ** 2))

    # Low energy ratio (fraction of frames with below-average energy)
    frame_size = 512
    energies = []
    for i in range(0, len(audio) - frame_size, frame_size):
        energies.append(np.sqrt(np.mean(audio[i:i+frame_size] ** 2)))
    if energies:
        mean_e = np.mean(energies)
        low_ratio = np.sum(np.array(energies) < mean_e) / len(energies)
    else:
        low_ratio = 0.5

    # Spectral rolloff (frequency below which 85% of energy is concentrated)
    cumsum = np.cumsum(fft)
    if cumsum[-1] > 0:
        rolloff_idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
        rolloff = freqs[min(rolloff_idx, len(freqs) - 1)]
    else:
        rolloff = 0.0

    return np.array([centroid, bandwidth, zcr, energy, low_ratio, rolloff])


class SpeakerDiarizer:
    """Simple speaker diarization using VAD + acoustic feature clustering."""

    def __init__(self, sample_rate: int = 16000, max_speakers: int = 4):
        self._sample_rate = sample_rate
        self._max_speakers = max_speakers
        self._vad = SimpleVAD(sample_rate=sample_rate)
        self._speaker_profiles: list[np.ndarray] = []
        self._similarity_threshold = 0.3

    def identify_speaker(self, audio: np.ndarray) -> int | None:
        """Identify speaker from an audio segment.

        Returns speaker index (0-based) or None if silence.
        """
        # Check if there's speech
        regions = self._vad.detect(audio)
        speech_frames = sum(1 for _, _, is_speech in regions if is_speech)
        if speech_frames < len(regions) * 0.3:
            return None  # Mostly silence

        features = _extract_features(audio, self._sample_rate)

        if not self._speaker_profiles:
            self._speaker_profiles.append(features)
            return 0

        # Find closest speaker
        min_dist = float("inf")
        closest = 0
        for i, profile in enumerate(self._speaker_profiles):
            dist = cosine(features, profile)
            if dist < min_dist:
                min_dist = dist
                closest = i

        if min_dist < self._similarity_threshold:
            # Update profile with exponential moving average
            alpha = 0.1
            self._speaker_profiles[closest] = (
                (1 - alpha) * self._speaker_profiles[closest] + alpha * features
            )
            return closest

        # New speaker
        if len(self._speaker_profiles) < self._max_speakers:
            self._speaker_profiles.append(features)
            return len(self._speaker_profiles) - 1

        # Max speakers reached, assign to closest
        return closest

    def reset(self):
        """Reset speaker profiles."""
        self._speaker_profiles.clear()

    @property
    def num_speakers(self) -> int:
        return len(self._speaker_profiles)
