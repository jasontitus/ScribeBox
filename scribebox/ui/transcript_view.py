"""Scrolling transcript display widget."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango


class TranscriptView(Gtk.ScrolledWindow):
    """Scrollable text view showing live transcription."""

    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self._textview = Gtk.TextView()
        self._textview.set_editable(False)
        self._textview.set_cursor_visible(False)
        self._textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._textview.set_left_margin(16)
        self._textview.set_right_margin(16)
        self._textview.set_top_margin(12)
        self._textview.set_bottom_margin(12)
        self._textview.get_style_context().add_class("transcript-view")

        self._buffer = self._textview.get_buffer()

        # Create text tags for speaker labels
        self._speaker_tags = {}
        for i in range(4):
            tag = self._buffer.create_tag(f"speaker-{i}")
            self._speaker_tags[i] = tag

        self._timestamp_tag = self._buffer.create_tag(
            "timestamp",
            scale=0.75,
            foreground="#888888",
        )

        self.add(self._textview)
        self._auto_scroll = True

        # Track scroll position
        vadj = self.get_vadjustment()
        vadj.connect("value-changed", self._on_scroll)

    def _on_scroll(self, adj):
        """Detect if user scrolled away from bottom."""
        at_bottom = adj.get_value() >= adj.get_upper() - adj.get_page_size() - 50
        self._auto_scroll = at_bottom

    def append_text(self, text: str, speaker: int | None = None,
                    timestamp: str | None = None):
        """Append transcribed text. Thread-safe via GLib.idle_add."""
        GLib.idle_add(self._do_append, text, speaker, timestamp)

    def _do_append(self, text: str, speaker: int | None, timestamp: str | None):
        end_iter = self._buffer.get_end_iter()

        # Add newline if buffer is not empty
        if self._buffer.get_char_count() > 0:
            self._buffer.insert(end_iter, "\n")
            end_iter = self._buffer.get_end_iter()

        # Timestamp
        if timestamp:
            start_mark = self._buffer.create_mark(None, end_iter, True)
            self._buffer.insert(end_iter, f"[{timestamp}] ")
            start_iter = self._buffer.get_iter_at_mark(start_mark)
            end_iter = self._buffer.get_end_iter()
            self._buffer.apply_tag(self._timestamp_tag, start_iter, end_iter)
            self._buffer.delete_mark(start_mark)
            end_iter = self._buffer.get_end_iter()

        # Speaker label
        if speaker is not None:
            label = f"Speaker {speaker + 1}: "
            start_mark = self._buffer.create_mark(None, end_iter, True)
            self._buffer.insert(end_iter, label)
            if speaker in self._speaker_tags:
                start_iter = self._buffer.get_iter_at_mark(start_mark)
                end_iter = self._buffer.get_end_iter()
                self._buffer.apply_tag(self._speaker_tags[speaker], start_iter, end_iter)
            self._buffer.delete_mark(start_mark)
            end_iter = self._buffer.get_end_iter()

        # Main text
        self._buffer.insert(end_iter, text)

        # Auto-scroll to bottom
        if self._auto_scroll:
            GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        adj = self.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def clear(self):
        """Clear all text."""
        GLib.idle_add(lambda: self._buffer.set_text(""))

    def get_full_text(self) -> str:
        """Get all text content."""
        start = self._buffer.get_start_iter()
        end = self._buffer.get_end_iter()
        return self._buffer.get_text(start, end, True)

    def set_speaker_colors(self, colors: list[str]):
        """Update speaker tag colors from theme."""
        for i, color in enumerate(colors):
            if i in self._speaker_tags:
                self._speaker_tags[i].set_property("foreground", color)
