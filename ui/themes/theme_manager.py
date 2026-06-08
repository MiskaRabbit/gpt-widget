"""
GPT Usage Widget — Theme Manager
Defines 5 built-in themes and provides QSS + color dict for each.
"""
from pathlib import Path
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QColor

THEMES_DIR = Path(__file__).parent

# ── Color palette for each theme (used by QPainter-based widgets) ──────────
THEMES: dict[str, dict] = {
    "dark_glass": {
        "name": "Dark Glass",
        "qss_file": "dark_glass.qss",
        "ring_bg":         QColor(255, 255, 255, 25),
        "ring_start":      QColor(99,  102, 241),
        "ring_end":        QColor(168,  85, 247),
        "ring_glow":       QColor(99,  102, 241, 100),
        "ring_width":      10,
        "chart_bar":       QColor(99,  102, 241),
        "chart_bar_today": QColor(168,  85, 247),
        "text_primary":    QColor(226, 232, 240),
        "text_secondary":  QColor(148, 163, 184),
        "accent":          QColor(99,  102, 241),
    },
    "neon_cyber": {
        "name": "Neon Cyber",
        "qss_file": "neon_cyber.qss",
        "ring_bg":         QColor(0, 255, 255, 20),
        "ring_start":      QColor(0, 255, 255),
        "ring_end":        QColor(255,  0, 255),
        "ring_glow":       QColor(0, 255, 255, 120),
        "ring_width":      8,
        "chart_bar":       QColor(0, 255, 200),
        "chart_bar_today": QColor(255,  0, 200),
        "text_primary":    QColor(200, 255, 255),
        "text_secondary":  QColor(0, 200, 200),
        "accent":          QColor(0, 255, 255),
    },
    "minimal_light": {
        "name": "Minimal Light",
        "qss_file": "minimal_light.qss",
        "ring_bg":         QColor(0, 0, 0, 18),
        "ring_start":      QColor(59, 130, 246),
        "ring_end":        QColor(99, 102, 241),
        "ring_glow":       QColor(59, 130, 246, 60),
        "ring_width":      9,
        "chart_bar":       QColor(59, 130, 246),
        "chart_bar_today": QColor(99, 102, 241),
        "text_primary":    QColor(15,  23,  42),
        "text_secondary":  QColor(100, 116, 139),
        "accent":          QColor(59, 130, 246),
    },
    "aurora": {
        "name": "Aurora Glow",
        "qss_file": "aurora.qss",
        "ring_bg":         QColor(255, 255, 255, 30),
        "ring_start":      QColor(52, 211, 153),
        "ring_end":        QColor(167,  85, 247),
        "ring_glow":       QColor(52, 211, 153, 100),
        "ring_width":      10,
        "chart_bar":       QColor(52, 211, 153),
        "chart_bar_today": QColor(251, 191,  36),
        "text_primary":    QColor(236, 253, 245),
        "text_secondary":  QColor(167, 243, 208),
        "accent":          QColor(52, 211, 153),
    },
    "retro_terminal": {
        "name": "Retro Terminal",
        "qss_file": "retro_terminal.qss",
        "ring_bg":         QColor(0, 255, 65, 20),
        "ring_start":      QColor(0, 255, 65),
        "ring_end":        QColor(0, 180, 50),
        "ring_glow":       QColor(0, 255, 65, 90),
        "ring_width":      8,
        "chart_bar":       QColor(0, 200, 50),
        "chart_bar_today": QColor(0, 255, 65),
        "text_primary":    QColor(0, 255, 65),
        "text_secondary":  QColor(0, 180, 50),
        "accent":          QColor(0, 255, 65),
    },
}

THEME_KEYS = list(THEMES.keys())


def get_theme(name: str) -> dict:
    return THEMES.get(name, THEMES["dark_glass"])


def load_qss(name: str) -> str:
    theme = get_theme(name)
    qss_path = THEMES_DIR / theme["qss_file"]
    try:
        return qss_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def apply_theme_to_widget(widget, name: str):
    """Apply QSS + repaint all themed child components."""
    qss = load_qss(name)
    widget.setStyleSheet(qss)
    theme_colors = get_theme(name)
    for child in widget.findChildren(QObject):
        if hasattr(child, "apply_theme"):
            child.apply_theme(theme_colors)
