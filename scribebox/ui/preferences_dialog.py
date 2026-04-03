"""Preferences dialog for configuring ScribeBox."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from scribebox.preferences import Preferences, AVAILABLE_MODELS
from scribebox.transcriber import list_available_models


class PreferencesDialog(Gtk.Dialog):
    """Settings dialog with all configurable options."""

    def __init__(self, parent, preferences: Preferences, models_dir: str | None = None):
        super().__init__(
            title="ScribeBox Preferences",
            transient_for=parent,
            flags=0,
        )
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY,
        )
        self.set_default_size(500, 600)
        self._prefs = preferences
        self._models_dir = models_dir
        self._widgets = {}
        self._build_ui()

    def _build_ui(self):
        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        notebook = Gtk.Notebook()
        content.pack_start(notebook, True, True, 0)

        # ── Transcription tab ──
        trans_grid = self._make_grid()
        notebook.append_page(trans_grid, Gtk.Label(label="Transcription"))

        row = 0

        # Model selection
        trans_grid.attach(Gtk.Label(label="Whisper Model:", halign=Gtk.Align.END), 0, row, 1, 1)
        model_combo = Gtk.ComboBoxText()
        model_combo.append("auto", "Auto-detect (recommended)")
        available = list_available_models(self._models_dir)
        for m in AVAILABLE_MODELS:
            label = m["name"]
            if m["id"] not in available:
                label += " (not downloaded)"
            model_combo.append(m["id"], label)
        current_model = self._prefs.get("model")
        model_combo.set_active_id(current_model if current_model else "auto")
        self._widgets["model"] = model_combo
        trans_grid.attach(model_combo, 1, row, 1, 1)
        row += 1

        # Language
        trans_grid.attach(Gtk.Label(label="Language:", halign=Gtk.Align.END), 0, row, 1, 1)
        lang_combo = Gtk.ComboBoxText()
        for lid, lname in [("en", "English"), ("auto", "Auto-detect"),
                           ("es", "Spanish"), ("fr", "French"), ("de", "German"),
                           ("it", "Italian"), ("pt", "Portuguese"), ("ja", "Japanese"),
                           ("zh", "Chinese"), ("ko", "Korean")]:
            lang_combo.append(lid, lname)
        lang_combo.set_active_id(self._prefs.get("language"))
        self._widgets["language"] = lang_combo
        trans_grid.attach(lang_combo, 1, row, 1, 1)
        row += 1

        # Diarization
        trans_grid.attach(Gtk.Label(label="Speaker Detection:", halign=Gtk.Align.END), 0, row, 1, 1)
        diar_switch = Gtk.Switch()
        diar_switch.set_active(self._prefs.get("diarization"))
        self._widgets["diarization"] = diar_switch
        box = Gtk.Box()
        box.pack_start(diar_switch, False, False, 0)
        trans_grid.attach(box, 1, row, 1, 1)
        row += 1

        # Summary window
        trans_grid.attach(Gtk.Label(label="Summary Window (sec):", halign=Gtk.Align.END), 0, row, 1, 1)
        summary_spin = Gtk.SpinButton.new_with_range(30, 600, 30)
        summary_spin.set_value(self._prefs.get("summary_window"))
        self._widgets["summary_window"] = summary_spin
        trans_grid.attach(summary_spin, 1, row, 1, 1)
        row += 1

        # Auto-save interval
        trans_grid.attach(Gtk.Label(label="Auto-save (sec):", halign=Gtk.Align.END), 0, row, 1, 1)
        save_spin = Gtk.SpinButton.new_with_range(10, 600, 10)
        save_spin.set_value(self._prefs.get("auto_save_interval"))
        self._widgets["auto_save_interval"] = save_spin
        trans_grid.attach(save_spin, 1, row, 1, 1)
        row += 1

        # ── Appearance tab ──
        appear_grid = self._make_grid()
        notebook.append_page(appear_grid, Gtk.Label(label="Appearance"))

        row = 0

        # Theme
        appear_grid.attach(Gtk.Label(label="Theme:", halign=Gtk.Align.END), 0, row, 1, 1)
        theme_combo = Gtk.ComboBoxText()
        for tid, tname in [("dark", "Dark"), ("light", "Light"),
                           ("high_contrast", "High Contrast")]:
            theme_combo.append(tid, tname)
        theme_combo.set_active_id(self._prefs.get("theme"))
        self._widgets["theme"] = theme_combo
        appear_grid.attach(theme_combo, 1, row, 1, 1)
        row += 1

        # Font size
        appear_grid.attach(Gtk.Label(label="Font Size:", halign=Gtk.Align.END), 0, row, 1, 1)
        font_spin = Gtk.SpinButton.new_with_range(14, 48, 2)
        font_spin.set_value(self._prefs.get("font_size"))
        self._widgets["font_size"] = font_spin
        appear_grid.attach(font_spin, 1, row, 1, 1)
        row += 1

        # Layout
        appear_grid.attach(Gtk.Label(label="Layout:", halign=Gtk.Align.END), 0, row, 1, 1)
        layout_combo = Gtk.ComboBoxText()
        for lid, lname in [("full", "Full Transcript"),
                           ("split", "Transcript + Summary"),
                           ("three-panel", "Transcript + Summary + Keywords")]:
            layout_combo.append(lid, lname)
        layout_combo.set_active_id(self._prefs.get("layout"))
        self._widgets["layout"] = layout_combo
        appear_grid.attach(layout_combo, 1, row, 1, 1)
        row += 1

        # Timestamps
        appear_grid.attach(Gtk.Label(label="Show Timestamps:", halign=Gtk.Align.END), 0, row, 1, 1)
        ts_switch = Gtk.Switch()
        ts_switch.set_active(self._prefs.get("show_timestamps"))
        self._widgets["show_timestamps"] = ts_switch
        box = Gtk.Box()
        box.pack_start(ts_switch, False, False, 0)
        appear_grid.attach(box, 1, row, 1, 1)
        row += 1

        # Font family
        appear_grid.attach(Gtk.Label(label="Font:", halign=Gtk.Align.END), 0, row, 1, 1)
        font_combo = Gtk.ComboBoxText()
        for f in ["monospace", "sans-serif", "serif"]:
            font_combo.append(f, f.title())
        font_combo.set_active_id(self._prefs.get("transcript_font"))
        self._widgets["transcript_font"] = font_combo
        appear_grid.attach(font_combo, 1, row, 1, 1)
        row += 1

        self.show_all()

    def _make_grid(self) -> Gtk.Grid:
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        return grid

    def get_updated_preferences(self) -> dict:
        """Extract preference values from the dialog widgets."""
        result = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, Gtk.ComboBoxText):
                result[key] = widget.get_active_id()
            elif isinstance(widget, Gtk.SpinButton):
                result[key] = int(widget.get_value())
            elif isinstance(widget, Gtk.Switch):
                result[key] = widget.get_active()
        return result
