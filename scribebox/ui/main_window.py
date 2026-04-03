"""Main application window for ScribeBox."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from scribebox.ui.transcript_view import TranscriptView
from scribebox.ui.summary_panel import SummaryPanel
from scribebox.ui.theme import get_theme, generate_css
from scribebox.preferences import Preferences


class MainWindow(Gtk.Window):
    """The main ScribeBox window."""

    def __init__(self, preferences: Preferences):
        super().__init__(title="ScribeBox")
        self._prefs = preferences
        self._recording = False

        # Fullscreen on the boot image, maximized in dev
        self.set_default_size(1024, 768)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self._on_key_press)

        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        # Main vertical box
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._main_box)

        # ── Header bar ──
        self._header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._header.get_style_context().add_class("header-bar")

        # Title
        title = Gtk.Label(label="ScribeBox")
        title.set_markup("<b>ScribeBox</b>")
        self._header.pack_start(title, False, False, 8)

        # Recording indicator
        self._rec_label = Gtk.Label()
        self._rec_label.get_style_context().add_class("recording-indicator")
        self._header.pack_start(self._rec_label, False, False, 8)

        # Status info (model, etc.)
        self._status_label = Gtk.Label(label="")
        self._status_label.set_halign(Gtk.Align.END)
        self._header.pack_end(self._status_label, False, False, 8)

        # Buttons
        self._prefs_btn = Gtk.Button(label="Preferences")
        self._prefs_btn.connect("clicked", self._on_prefs_clicked)
        self._header.pack_end(self._prefs_btn, False, False, 4)

        self._benchmark_btn = Gtk.Button(label="Benchmark")
        self._benchmark_btn.connect("clicked", self._on_benchmark_clicked)
        self._header.pack_end(self._benchmark_btn, False, False, 4)

        self._record_btn = Gtk.Button(label="Start Recording")
        self._record_btn.connect("clicked", self._on_record_clicked)
        self._header.pack_end(self._record_btn, False, False, 4)

        self._save_btn = Gtk.Button(label="Save Transcript")
        self._save_btn.connect("clicked", self._on_save_clicked)
        self._header.pack_end(self._save_btn, False, False, 4)

        self._main_box.pack_start(self._header, False, False, 0)

        # ── Content area ──
        self._content = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self._main_box.pack_start(self._content, True, True, 0)

        # Transcript view (top)
        self.transcript_view = TranscriptView()
        self._content.pack1(self.transcript_view, resize=True, shrink=False)

        # Summary panel (bottom)
        self.summary_panel = SummaryPanel()
        self._content.pack2(self.summary_panel, resize=False, shrink=False)

        # Set initial split position (70/30)
        self._content.set_position(500)

        # ── Status bar ──
        self._statusbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._statusbar.get_style_context().add_class("status-bar")
        self._statusbar_label = Gtk.Label(label="Ready - Press F5 to start recording")
        self._statusbar_label.set_halign(Gtk.Align.START)
        self._statusbar.pack_start(self._statusbar_label, True, True, 0)
        self._main_box.pack_end(self._statusbar, False, False, 0)

        # Handle layout preference
        layout = self._prefs.get("layout")
        if layout == "full":
            self.summary_panel.hide()

    def _apply_theme(self):
        theme = get_theme(self._prefs.get("theme"))
        css = generate_css(
            theme,
            font_size=self._prefs.get("font_size"),
            font_family=self._prefs.get("transcript_font"),
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        # Update speaker colors
        self.transcript_view.set_speaker_colors(theme["speaker_colors"])

    def _on_key_press(self, widget, event):
        """Handle keyboard shortcuts."""
        key = Gdk.keyval_name(event.keyval)
        if key == "F5":
            self._on_record_clicked(None)
        elif key == "F11":
            self._toggle_fullscreen()
        elif key == "F2":
            self._on_prefs_clicked(None)
        elif key == "Escape":
            if self._recording:
                self._on_record_clicked(None)  # Stop

    def _toggle_fullscreen(self):
        # Simple toggle using window state
        if self.get_window():
            state = self.get_window().get_state()
            if state & Gdk.WindowState.FULLSCREEN:
                self.unfullscreen()
            else:
                self.fullscreen()

    def _on_record_clicked(self, _btn):
        """Toggle recording. The actual start/stop is handled by the app."""
        # This will be connected to the app's controller
        pass

    def _on_prefs_clicked(self, _btn):
        """Open preferences. Connected by the app."""
        pass

    def _on_benchmark_clicked(self, _btn):
        """Open benchmark. Connected by the app."""
        pass

    def _on_save_clicked(self, _btn):
        """Save transcript. Connected by the app."""
        pass

    def set_recording_state(self, recording: bool, model_name: str = ""):
        """Update UI for recording state."""
        self._recording = recording
        if recording:
            self._rec_label.set_markup('<span foreground="red">&#9679; RECORDING</span>')
            self._record_btn.set_label("Stop Recording")
            self._statusbar_label.set_text(f"Recording with {model_name}...")
        else:
            self._rec_label.set_text("")
            self._record_btn.set_label("Start Recording")
            self._statusbar_label.set_text("Ready - Press F5 to start recording")

    def set_status(self, text: str):
        """Update status bar text."""
        GLib.idle_add(self._statusbar_label.set_text, text)

    def set_model_info(self, text: str):
        """Update model info in header."""
        GLib.idle_add(self._status_label.set_text, text)

    def refresh_theme(self):
        """Re-apply theme from current preferences."""
        self._apply_theme()
        layout = self._prefs.get("layout")
        if layout == "full":
            self.summary_panel.hide()
        else:
            self.summary_panel.show()
