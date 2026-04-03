"""Audio capture via sounddevice (ALSA backend on Linux).

Captures 16kHz mono audio in chunks for streaming to whisper.cpp.
"""

import queue
import threading
import numpy as np


class AudioCapture:
    """Captures audio from the default input device."""

    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = np.float32
    # 2-second chunks for whisper processing
    CHUNK_DURATION = 2.0

    def __init__(self, device=None, chunk_duration: float | None = None):
        self._device = device
        self._chunk_duration = chunk_duration or self.CHUNK_DURATION
        self._chunk_samples = int(self.SAMPLE_RATE * self._chunk_duration)
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=30)
        self._running = False
        self._stream = None
        self._buffer = np.array([], dtype=self.DTYPE)
        self._lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            pass  # Silently handle xruns on slow hardware
        audio = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
        with self._lock:
            self._buffer = np.concatenate([self._buffer, audio])
            while len(self._buffer) >= self._chunk_samples:
                chunk = self._buffer[:self._chunk_samples]
                self._buffer = self._buffer[self._chunk_samples:]
                try:
                    self._queue.put_nowait(chunk)
                except queue.Full:
                    # Drop oldest chunk if consumer is too slow
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queue.put_nowait(chunk)

    def start(self):
        """Start capturing audio."""
        import sounddevice as sd
        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            device=self._device,
            blocksize=int(self.SAMPLE_RATE * 0.1),  # 100ms blocks
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self):
        """Stop capturing audio."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_chunk(self, timeout: float = 5.0) -> np.ndarray | None:
        """Get the next audio chunk. Returns None on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        import sounddevice as sd
        devices = sd.query_devices()
        inputs = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                inputs.append({
                    "index": i,
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                    "sample_rate": d["default_samplerate"],
                })
        return inputs
