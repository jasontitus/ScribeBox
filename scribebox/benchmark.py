"""Hardware benchmark tool for ScribeBox.

Tests different Whisper models to determine what the hardware can handle
for real-time transcription. Generates a short test audio clip and measures
inference time vs audio duration.
"""

import os
import sys
import time
import json
import struct
import subprocess
import tempfile

import numpy as np

from scribebox.transcriber import get_model_path, list_available_models, _find_whisper_binary
from scribebox.preferences import AVAILABLE_MODELS


def _generate_test_audio(duration: float = 5.0, sample_rate: int = 16000) -> np.ndarray:
    """Generate a test audio signal (speech-like noise for benchmarking).

    Uses a mix of tones and noise to simulate speech characteristics.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    # Fundamental frequency sweep (80-300 Hz, speech range)
    f0 = 120 + 50 * np.sin(2 * np.pi * 0.5 * t)
    signal = 0.3 * np.sin(2 * np.pi * f0 * t)
    # Add harmonics
    signal += 0.15 * np.sin(2 * np.pi * 2 * f0 * t)
    signal += 0.08 * np.sin(2 * np.pi * 3 * f0 * t)
    # Add some noise
    signal += 0.05 * np.random.randn(len(t)).astype(np.float32)
    # Envelope (simulate syllables)
    envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)
    signal *= envelope
    # Normalize
    signal = signal / np.max(np.abs(signal)) * 0.8
    return signal


def _write_wav_file(audio: np.ndarray, path: str, sample_rate: int = 16000):
    """Write float32 audio to a WAV file."""
    pcm = (audio * 32767).astype(np.int16)
    data = pcm.tobytes()
    with open(path, "wb") as f:
        f.write(struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + len(data), b"WAVE", b"fmt ", 16,
            1, 1, sample_rate, sample_rate * 2, 2, 16,
            b"data", len(data),
        ))
        f.write(data)


def _get_system_info() -> dict:
    """Gather system hardware info."""
    info = {
        "cpu": "Unknown",
        "cores": os.cpu_count() or 1,
        "ram_mb": 0,
        "cpu_flags": [],
    }

    # CPU info
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("model name"):
                    info["cpu"] = line.split(":")[1].strip()
                    break
                if "flags" in line:
                    flags = line.split(":")[1].strip().split()
                    info["cpu_flags"] = [f for f in flags
                                         if f in ("sse3", "ssse3", "sse4_1", "sse4_2",
                                                   "avx", "avx2", "fma", "f16c")]
    except OSError:
        pass

    # RAM
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    info["ram_mb"] = kb // 1024
                    break
    except OSError:
        pass

    return info


def benchmark_model(model_id: str, models_dir: str | None = None,
                    test_duration: float = 5.0, threads: int | None = None) -> dict:
    """Benchmark a single Whisper model.

    Returns dict with:
        model_id, inference_time, audio_duration, real_time_factor,
        can_realtime, error
    """
    binary = _find_whisper_binary()
    if not binary:
        return {"model_id": model_id, "error": "whisper-cli binary not found"}

    model_path = get_model_path(model_id, models_dir)
    if not model_path:
        return {"model_id": model_id, "error": f"Model file not found for {model_id}"}

    if threads is None:
        try:
            threads = len(os.sched_getaffinity(0))
        except AttributeError:
            threads = 2

    audio = _generate_test_audio(test_duration)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_wav_file(audio, f.name)
        wav_path = f.name

    try:
        cmd = [
            binary,
            "-m", model_path,
            "-f", wav_path,
            "-t", str(threads),
            "--no-timestamps",
            "-nt",
        ]

        start = time.monotonic()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        elapsed = time.monotonic() - start

        rtf = elapsed / test_duration

        return {
            "model_id": model_id,
            "inference_time": round(elapsed, 2),
            "audio_duration": test_duration,
            "real_time_factor": round(rtf, 2),
            "can_realtime": rtf < 1.0,
            "threads": threads,
            "error": None if result.returncode == 0 else result.stderr[:200],
        }

    except subprocess.TimeoutExpired:
        return {
            "model_id": model_id,
            "inference_time": 120.0,
            "audio_duration": test_duration,
            "real_time_factor": 120.0 / test_duration,
            "can_realtime": False,
            "error": "Timed out (>120s)",
        }
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


def run_full_benchmark(models_dir: str | None = None,
                       test_duration: float = 5.0) -> dict:
    """Run benchmark on all available models.

    Returns dict with system_info, results list, and recommended model.
    """
    sys_info = _get_system_info()
    available = list_available_models(models_dir)

    results = []
    for model_id in available:
        print(f"  Benchmarking {model_id}...", flush=True)
        result = benchmark_model(model_id, models_dir, test_duration)
        results.append(result)
        if result.get("error"):
            print(f"    Error: {result['error']}")
        else:
            rtf = result["real_time_factor"]
            status = "REALTIME" if result["can_realtime"] else "TOO SLOW"
            print(f"    RTF: {rtf:.2f}x ({status})")

    # Find best model that can do real-time
    realtime_models = [r for r in results if r.get("can_realtime")]
    if realtime_models:
        # Pick the largest model that can still do real-time
        model_order = [m["id"] for m in AVAILABLE_MODELS]
        best = max(realtime_models,
                   key=lambda r: model_order.index(r["model_id"])
                   if r["model_id"] in model_order else -1)
        recommended = best["model_id"]
    elif results:
        # Nothing can do real-time, pick the fastest
        best = min(results, key=lambda r: r.get("real_time_factor", 999))
        recommended = best["model_id"]
    else:
        recommended = "tiny.en"

    return {
        "system_info": sys_info,
        "results": results,
        "recommended_model": recommended,
    }


def auto_select_model(models_dir: str | None = None) -> str:
    """Auto-select a model based on available RAM (no benchmark, instant).

    This is the fast path used when model is set to 'auto'.
    """
    sys_info = _get_system_info()
    ram = sys_info["ram_mb"]
    available = set(list_available_models(models_dir))

    # Simple heuristic based on RAM
    if ram >= 4096 and "small.en" in available:
        return "small.en"
    if ram >= 4096 and "small.en-q5" in available:
        return "small.en-q5"
    if ram >= 2048 and "base.en" in available:
        return "base.en"
    if "tiny.en" in available:
        return "tiny.en"
    if "tiny" in available:
        return "tiny"

    # Fallback to whatever is available
    if available:
        return min(available)
    return "tiny.en"


def run_benchmark_cli(models_dir: str | None = None):
    """CLI entry point for the benchmark."""
    print("=" * 60)
    print("  ScribeBox Hardware Benchmark")
    print("=" * 60)
    print()

    sys_info = _get_system_info()
    print(f"  CPU:    {sys_info['cpu']}")
    print(f"  Cores:  {sys_info['cores']}")
    print(f"  RAM:    {sys_info['ram_mb']} MB")
    if sys_info['cpu_flags']:
        print(f"  SIMD:   {', '.join(sys_info['cpu_flags'])}")
    print()

    available = list_available_models(models_dir)
    if not available:
        print("  No models found! Run scripts/download-models.sh first.")
        print(f"  Models directory: {models_dir or 'default'}")
        return

    print(f"  Found {len(available)} models: {', '.join(available)}")
    print()
    print("  Running benchmarks (5 seconds of audio each)...")
    print()

    report = run_full_benchmark(models_dir)

    print()
    print("-" * 60)
    print("  Results:")
    print(f"  {'Model':<20} {'RTF':>8} {'Time':>8} {'Status':>12}")
    print("-" * 60)
    for r in report["results"]:
        if r.get("error"):
            status = "ERROR"
        elif r["can_realtime"]:
            status = "REALTIME"
        else:
            status = "TOO SLOW"
        print(f"  {r['model_id']:<20} {r.get('real_time_factor', 0):>7.2f}x "
              f"{r.get('inference_time', 0):>7.1f}s {status:>12}")

    print()
    print(f"  Recommended model: {report['recommended_model']}")
    print()

    # Save results
    results_path = os.path.join(
        models_dir or os.path.expanduser("~/.local/share/scribebox"),
        "benchmark_results.json"
    )
    try:
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        with open(results_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Results saved to: {results_path}")
    except OSError:
        pass
