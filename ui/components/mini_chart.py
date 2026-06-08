"""
GPT Usage Widget — Mini Bar Chart (7-day trend)
Custom QPainter widget showing daily spending as vertical gradient bars.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QBrush,
                          QPen, QFont)


class MiniChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(240, 80)
        self._data: list[tuple[str, float]] = []  # [(label, value), ...]
        self._highlight_last: bool = True

        # Theme colors
        self._bar_color = QColor(99, 102, 241)
        self._bar_highlight = QColor(168, 85, 247)
        self._bar_alpha = 200
        self._text_color = QColor(148, 163, 184)
        self._zero_color = QColor(255, 255, 255, 20)

    def set_data(self, data: list[tuple[str, float]]):
        """data: list of (short_label, value). Last item = today (highlighted)."""
        self._data = data
        self.update()

    def apply_theme(self, theme: dict):
        self._bar_color = theme.get("chart_bar", self._bar_color)
        self._bar_highlight = theme.get("chart_bar_today", self._bar_highlight)
        self._text_color = theme.get("text_secondary", self._text_color)
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        label_h = 16
        chart_h = h - label_h - 4
        n = len(self._data)

        gap = 4
        bar_w = (w - gap * (n - 1)) / n
        max_val = max((v for _, v in self._data), default=1.0) or 1.0

        for i, (label, value) in enumerate(self._data):
            x = i * (bar_w + gap)
            ratio = value / max_val
            bar_h = max(3.0, ratio * (chart_h - 4))
            bar_y = chart_h - bar_h

            is_last = (i == n - 1) and self._highlight_last

            # Bar gradient
            rect = QRectF(x, bar_y, bar_w, bar_h)
            if value > 0:
                grad = QLinearGradient(QPointF(x, bar_y), QPointF(x, bar_y + bar_h))
                top_c = QColor(self._bar_highlight if is_last else self._bar_color)
                bot_c = QColor(self._bar_color)
                bot_c.setAlpha(120)
                grad.setColorAt(0.0, top_c)
                grad.setColorAt(1.0, bot_c)
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                # Rounded top corners
                painter.drawRoundedRect(rect, 3, 3)
            else:
                painter.setBrush(self._zero_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(x, chart_h - 3, bar_w, 3), 1, 1)

            # Label
            painter.setPen(QPen(self._text_color))
            font = QFont("Segoe UI", 7)
            painter.setFont(font)
            painter.drawText(
                QRectF(x, chart_h + 4, bar_w, label_h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )
