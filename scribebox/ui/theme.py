"""Theme definitions for ScribeBox UI."""

THEMES = {
    "dark": {
        "name": "Dark",
        "bg": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_panel": "#0f3460",
        "text": "#e0e0e0",
        "text_secondary": "#a0a0a0",
        "accent": "#e94560",
        "speaker_colors": ["#53c9b1", "#e9a645", "#c95390", "#4590e9"],
        "border": "#2a2a4a",
        "scrollbar": "#3a3a5a",
        "button_bg": "#0f3460",
        "button_hover": "#1a4a7a",
    },
    "light": {
        "name": "Light",
        "bg": "#fafafa",
        "bg_secondary": "#f0f0f0",
        "bg_panel": "#e8e8e8",
        "text": "#1a1a1a",
        "text_secondary": "#666666",
        "accent": "#d63031",
        "speaker_colors": ["#00b894", "#e17055", "#6c5ce7", "#0984e3"],
        "border": "#d0d0d0",
        "scrollbar": "#c0c0c0",
        "button_bg": "#e0e0e0",
        "button_hover": "#d0d0d0",
    },
    "high_contrast": {
        "name": "High Contrast",
        "bg": "#000000",
        "bg_secondary": "#111111",
        "bg_panel": "#1a1a1a",
        "text": "#ffffff",
        "text_secondary": "#cccccc",
        "accent": "#ffff00",
        "speaker_colors": ["#00ff00", "#ff6600", "#ff00ff", "#00ffff"],
        "border": "#ffffff",
        "scrollbar": "#666666",
        "button_bg": "#333333",
        "button_hover": "#555555",
    },
}


def get_theme(name: str) -> dict:
    """Get a theme by name. Falls back to dark."""
    return THEMES.get(name, THEMES["dark"])


def generate_css(theme: dict, font_size: int = 24, font_family: str = "monospace") -> str:
    """Generate GTK CSS from a theme dict."""
    return f"""
    window {{
        background-color: {theme['bg']};
    }}
    .transcript-view {{
        background-color: {theme['bg']};
        color: {theme['text']};
        font-family: {font_family};
        font-size: {font_size}px;
        padding: 16px;
    }}
    .transcript-view text {{
        background-color: {theme['bg']};
        color: {theme['text']};
    }}
    .summary-panel {{
        background-color: {theme['bg_panel']};
        color: {theme['text_secondary']};
        font-family: {font_family};
        font-size: {max(14, font_size - 6)}px;
        padding: 12px;
        border-top: 2px solid {theme['border']};
    }}
    .summary-panel text {{
        background-color: {theme['bg_panel']};
        color: {theme['text_secondary']};
    }}
    .summary-label {{
        color: {theme['accent']};
        font-weight: bold;
        font-size: {max(12, font_size - 8)}px;
    }}
    .keyword-label {{
        color: {theme['accent']};
        font-size: {max(12, font_size - 10)}px;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: {theme['bg_secondary']};
    }}
    .status-bar {{
        background-color: {theme['bg_secondary']};
        color: {theme['text_secondary']};
        font-size: 13px;
        padding: 4px 12px;
        border-top: 1px solid {theme['border']};
    }}
    .header-bar {{
        background-color: {theme['bg_secondary']};
        color: {theme['text']};
        padding: 6px 12px;
        border-bottom: 1px solid {theme['border']};
    }}
    .speaker-0 {{ color: {theme['speaker_colors'][0]}; font-weight: bold; }}
    .speaker-1 {{ color: {theme['speaker_colors'][1]}; font-weight: bold; }}
    .speaker-2 {{ color: {theme['speaker_colors'][2]}; font-weight: bold; }}
    .speaker-3 {{ color: {theme['speaker_colors'][3]}; font-weight: bold; }}
    button {{
        background-color: {theme['button_bg']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 6px 16px;
        min-height: 32px;
    }}
    button:hover {{
        background-color: {theme['button_hover']};
    }}
    .recording-indicator {{
        color: {theme['accent']};
        font-size: 14px;
        font-weight: bold;
    }}
    """
