"""Lightweight speaker diarization using VAD and MFCC-based clustering.

Designed for 2-speaker scenarios on old hardware.
Uses energy-based VAD for speech detection and MFCC features for speaker identification.
"""

import numpy as np
from scipy.spatial.distance import euclidean


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
    """Extract acoustic features for speaker identification.

    Uses MFCCs (Mel-Frequency Cepstral Coefficients) computed from scratch.
    Returns a 13-dimensional feature vector (mean MFCCs across frames).
    MFCCs capture the spectral envelope of speech and are the standard
    feature for speaker identification.
    """
    if len(audio) < 512:
        return np.zeros(13)

    # Parameters
    n_fft = 512
    hop = 160  # 10ms at 16kHz
    n_mels = 26
    n_mfcc = 13

    # Pre-emphasis
    emphasized = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])

    # Frame the signal
    n_frames = 1 + (len(emphasized) - n_fft) // hop
    if n_frames < 1:
        return np.zeros(n_mfcc)

    frames = np.zeros((n_frames, n_fft), dtype=np.float32)
    for i in range(n_frames):
        start = i * hop
        frames[i] = emphasized[start:start + n_fft]

    # Apply Hamming window
    window = np.hamming(n_fft).astype(np.float32)
    frames *= window

    # Power spectrum
    power = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2

    # Mel filterbank
    low_freq_mel = 0
    high_freq_mel = 2595 * np.log10(1 + (sample_rate / 2) / 700)
    mel_points = np.linspace(low_freq_mel, high_freq_mel, n_mels + 2)
    hz_points = 700 * (10 ** (mel_points / 2595) - 1)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)

    filterbank = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(n_mels):
        f_left = bin_points[m]
        f_center = bin_points[m + 1]
        f_right = bin_points[m + 2]
        for k in range(f_left, f_center):
            if f_center > f_left:
                filterbank[m, k] = (k - f_left) / (f_center - f_left)
        for k in range(f_center, f_right):
            if f_right > f_center:
                filterbank[m, k] = (f_right - k) / (f_right - f_center)

    # Apply filterbank and take log
    mel_spec = np.dot(power, filterbank.T)
    mel_spec = np.maximum(mel_spec, 1e-10)
    log_mel = np.log(mel_spec)

    # DCT to get MFCCs
    mfccs = np.zeros((n_frames, n_mfcc))
    for i in range(n_mfcc):
        mfccs[:, i] = np.sum(
            log_mel * np.cos(np.pi * i * (np.arange(n_mels) + 0.5) / n_mels),
            axis=1,
        )

    # Return mean MFCCs across all frames (speaker "fingerprint")
    return np.mean(mfccs, axis=0)


class SpeakerDiarizer:
    """Simple speaker diarization using VAD + acoustic feature clustering."""

    def __init__(self, sample_rate: int = 16000, max_speakers: int = 4):
        self._sample_rate = sample_rate
        self._max_speakers = max_speakers
        self._vad = SimpleVAD(sample_rate=sample_rate)
        self._speaker_profiles: list[np.ndarray] = []
        self._distance_threshold = 15.0  # Euclidean distance on MFCCs

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

        # Find closest speaker using Euclidean distance on MFCCs
        min_dist = float("inf")
        closest = 0
        for i, profile in enumerate(self._speaker_profiles):
            dist = euclidean(features, profile)
            if dist < min_dist:
                min_dist = dist
                closest = i

        if min_dist < self._distance_threshold:
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
