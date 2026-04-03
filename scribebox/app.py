"""Main ScribeBox application controller.

Connects the UI, audio capture, transcription, summarization, and diarization.
"""

import os
import time
import threading
from datetime import datetime

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from scribebox.preferences import Preferences
from scribebox.audio import AudioCapture
from scribebox.transcriber import Transcriber, StreamingTranscriber, list_available_models
from scribebox.summarizer import RollingSummarizer
from scribebox.diarizer import SpeakerDiarizer
from scribebox.benchmark import auto_select_model, run_full_benchmark
from scribebox.ui.main_window import MainWindow
from scribebox.ui.preferences_dialog import PreferencesDialog


class ScribeBoxApp:
    """Main application orchestrator."""

    def __init__(self, models_dir: str | None = None, data_dir: str | None = None,
                 open_preferences: bool = False):
        self._models_dir = models_dir
        self._prefs = Preferences(data_dir=data_dir)
        self._open_preferences = open_preferences

        # Core components (initialized lazily)
        self._audio: AudioCapture | None = None
        self._transcriber: Transcriber | None = None
        self._streamer: StreamingTranscriber | None = None
        self._summarizer = RollingSummarizer(
            window_seconds=self._prefs.get("summary_window")
        )
        self._diarizer = SpeakerDiarizer() if self._prefs.get("diarization") else None

        self._recording = False
        self._session_text: list[str] = []  # Full session transcript
        self._start_time: float = 0
        self._auto_save_timer = None

        # Resolve model
        self._model_id = self._resolve_model()

    def _resolve_model(self) -> str:
        """Determine which model to use."""
        model = self._prefs.get("model")
        if model == "auto":
            return auto_select_model(self._models_dir)
        return model

    def run(self):
        """Start the GTK application."""
        self._window = MainWindow(self._prefs)
        self._connect_signals()

        # Show model info
        available = list_available_models(self._models_dir)
        self._window.set_model_info(f"Model: {self._model_id} | {len(available)} models loaded")

        if self._open_preferences:
            GLib.idle_add(self._show_preferences)

        self._window.show_all()

        # Hide summary panel if layout is "full"
        if self._prefs.get("layout") == "full":
            self._window.summary_panel.hide()

        Gtk.main()

    def _connect_signals(self):
        """Wire up button callbacks."""
        self._window._record_btn.connect("clicked", lambda _: self._toggle_recording())
        self._window._prefs_btn.connect("clicked", lambda _: self._show_preferences())
        self._window._benchmark_btn.connect("clicked", lambda _: self._run_benchmark())
        self._window._save_btn.connect("clicked", lambda _: self._save_transcript())
        # Override key handler
        self._window.connect("key-press-event", self._on_key_press)

    def _on_key_press(self, widget, event):
        from gi.repository import Gdk
        key = Gdk.keyval_name(event.keyval)
        if key == "F5":
            self._toggle_recording()
            return True
        elif key == "F11":
            self._window._toggle_fullscreen()
            return True
        elif key == "F2":
            self._show_preferences()
            return True
        elif key == "Escape" and self._recording:
            self._toggle_recording()
            return True
        return False

    def _toggle_recording(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start audio capture and transcription."""
        self._window.set_status("Initializing...")

        # Create transcriber
        self._transcriber = Transcriber(
            model_id=self._model_id,
            models_dir=self._models_dir,
            language=self._prefs.get("language"),
        )

        if not self._transcriber.is_ready():
            self._window.set_status(
                f"Error: Model '{self._model_id}' not found. "
                "Run the benchmark or check models directory."
            )
            return

        # Create audio capture
        self._audio = AudioCapture(chunk_duration=3.0)

        # Reset summarizer
        self._summarizer = RollingSummarizer(
            window_seconds=self._prefs.get("summary_window")
        )

        # Reset diarizer
        if self._prefs.get("diarization"):
            self._diarizer = SpeakerDiarizer()
        else:
            self._diarizer = None

        self._start_time = time.time()
        self._session_text.clear()

        # Create streaming transcriber
        self._streamer = StreamingTranscriber(
            transcriber=self._transcriber,
            on_text=self._on_transcription,
            on_error=self._on_error,
        )

        try:
            self._audio.start()
            self._streamer.start(self._audio)
            self._recording = True
            self._window.set_recording_state(True, self._model_id)

            # Start auto-save timer
            interval = self._prefs.get("auto_save_interval") * 1000
            self._auto_save_timer = GLib.timeout_add(interval, self._auto_save)

            # Start summary update timer
            GLib.timeout_add(5000, self._update_summary)

        except Exception as e:
            self._window.set_status(f"Error starting audio: {e}")
            self._stop_recording()

    def _stop_recording(self):
        """Stop audio capture and transcription."""
        self._recording = False

        if self._streamer:
            self._streamer.stop()
            self._streamer = None

        if self._audio:
            self._audio.stop()
            self._audio = None

        if self._auto_save_timer:
            GLib.source_remove(self._auto_save_timer)
            self._auto_save_timer = None

        self._window.set_recording_state(False)
        self._auto_save()  # Final save

    def _on_transcription(self, text: str):
        """Callback when new text is transcribed (called from background thread)."""
        if not text.strip():
            return

        now = time.time()
        elapsed = now - self._start_time
        timestamp = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"

        # Speaker identification
        speaker = None
        if self._diarizer and self._audio:
            # Use the audio chunk for diarization
            # Note: simplified - in production would pass the actual audio
            pass

        self._session_text.append(text)
        self._summarizer.add_text(text, now)

        show_ts = self._prefs.get("show_timestamps")
        self._window.transcript_view.append_text(
            text,
            speaker=speaker,
            timestamp=timestamp if show_ts else None,
        )

    def _on_error(self, error: str):
        """Callback for transcription errors."""
        GLib.idle_add(self._window.set_status, f"Error: {error}")

    def _update_summary(self) -> bool:
        """Periodically update the summary panel."""
        if not self._recording:
            return False  # Stop the timer

        summary = self._summarizer.get_summary()
        keywords = self._summarizer.get_keywords()
        self._window.summary_panel.update_summary(summary, keywords)
        return True  # Continue timer

    def _auto_save(self) -> bool:
        """Auto-save transcript to disk."""
        if not self._session_text:
            return self._recording

        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transcript_{ts}.txt"
            path = os.path.join(self._prefs.transcripts_dir, filename)
            with open(path, "w") as f:
                f.write("\n".join(self._session_text))
        except OSError:
            pass
        return self._recording  # Continue timer if still recording

    def _save_transcript(self):
        """Manually save current transcript."""
        if not self._session_text:
            self._window.set_status("Nothing to save")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{ts}.txt"
        path = os.path.join(self._prefs.transcripts_dir, filename)
        try:
            with open(path, "w") as f:
                f.write("\n".join(self._session_text))
            self._window.set_status(f"Saved to {path}")
        except OSError as e:
            self._window.set_status(f"Save error: {e}")

    def _show_preferences(self):
        """Open the preferences dialog."""
        dialog = PreferencesDialog(self._window, self._prefs, self._models_dir)
        response = dialog.run()

        if response == Gtk.ResponseType.APPLY:
            updates = dialog.get_updated_preferences()
            for key, value in updates.items():
                self._prefs.set(key, value)
            self._prefs.save()

            # Apply changes
            self._model_id = self._resolve_model()
            self._window.set_model_info(f"Model: {self._model_id}")
            self._window.refresh_theme()

            if self._prefs.get("diarization"):
                self._diarizer = SpeakerDiarizer()
            else:
                self._diarizer = None

        dialog.destroy()

    def _run_benchmark(self):
        """Run benchmark in a background thread with progress dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self._window,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text="Running Benchmark...",
        )
        dialog.format_secondary_text(
            "Testing all available models. This may take a few minutes."
        )
        dialog.show()

        def do_benchmark():
            report = run_full_benchmark(self._models_dir)
            GLib.idle_add(show_results, report)

        def show_results(report):
            dialog.destroy()

            # Build results text
            lines = ["Hardware Benchmark Results\n"]
            info = report["system_info"]
            lines.append(f"CPU: {info['cpu']}")
            lines.append(f"RAM: {info['ram_mb']} MB")
            lines.append(f"Cores: {info['cores']}")
            lines.append("")

            for r in report["results"]:
                if r.get("error"):
                    lines.append(f"  {r['model_id']}: ERROR - {r['error']}")
                else:
                    status = "REALTIME" if r["can_realtime"] else "TOO SLOW"
                    lines.append(
                        f"  {r['model_id']}: {r['real_time_factor']:.2f}x ({status})"
                    )

            lines.append(f"\nRecommended: {report['recommended_model']}")

            result_dialog = Gtk.MessageDialog(
                transient_for=self._window,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Benchmark Complete",
            )
            result_dialog.format_secondary_text("\n".join(lines))

            # Offer to apply recommended model
            result_dialog.add_button("Use Recommended", Gtk.ResponseType.APPLY)
            response = result_dialog.run()

            if response == Gtk.ResponseType.APPLY:
                self._prefs.set("model", report["recommended_model"])
                self._prefs.save()
                self._model_id = report["recommended_model"]
                self._window.set_model_info(f"Model: {self._model_id}")

            result_dialog.destroy()

        thread = threading.Thread(target=do_benchmark, daemon=True)
        thread.start()
