"""Rolling summary panel shown below the transcript."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class SummaryPanel(Gtk.Box):
    """Panel showing rolling summary and keywords."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_style_context().add_class("summary-panel")
        self.set_size_request(-1, 120)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label="Summary (last 2 min)")
        label.get_style_context().add_class("summary-label")
        label.set_halign(Gtk.Align.START)
        header.pack_start(label, False, False, 0)

        self._keywords_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.pack_end(self._keywords_box, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Summary text
        self._textview = Gtk.TextView()
        self._textview.set_editable(False)
        self._textview.set_cursor_visible(False)
        self._textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._textview.get_style_context().add_class("summary-panel")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add(self._textview)

        self.pack_start(scroll, True, True, 0)

    def update_summary(self, summary_text: str, keywords: list[str] | None = None):
        """Update the summary text and keywords. Thread-safe."""
        GLib.idle_add(self._do_update, summary_text, keywords)

    def _do_update(self, summary_text: str, keywords: list[str] | None):
        buf = self._textview.get_buffer()
        buf.set_text(summary_text)

        # Update keywords
        for child in self._keywords_box.get_children():
            self._keywords_box.remove(child)

        if keywords:
            for kw in keywords[:5]:
                label = Gtk.Label(label=kw)
                label.get_style_context().add_class("keyword-label")
                self._keywords_box.pack_start(label, False, False, 0)
            self._keywords_box.show_all()

    def clear(self):
        """Clear summary."""
        GLib.idle_add(lambda: self._textview.get_buffer().set_text(""))
