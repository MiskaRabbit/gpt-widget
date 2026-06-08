"""
GPT Usage Widget — Circular Progress Ring
Custom QPainter widget with gradient arc, glow effect, and center text.
"""
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QPen, QColor, QConicalGradient, QBrush, QFont, QRadialGradient


class ProgressRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(84, 84)
        self._value: float = 0.0          # 0–100
        self._animated_value: float = 0.0
        self._pen_width: int = 10

        # Default colors (overridden by theme)
        self._bg_color = QColor(255, 255, 255, 25)
        self._color_start = QColor(99, 102, 241)
        self._color_end = QColor(168, 85, 247)
        self._glow_color = QColor(99, 102, 241, 80)
        self._text_color = QColor(226, 232, 240)
        self._sub_text_color = QColor(148, 163, 184)
        self._center_label: str = ""
        self._sub_label: str = ""
        self._compact_text = False

        self._anim = QPropertyAnimation(self, b"animatedValue", self)
        self._anim.setDuration(800)

    # ─── Properties ────────────────────────────────────────────────────────────

    def get_animated_value(self) -> float:
        return self._animated_value

    def set_animated_value(self, v: float):
        self._animated_value = v
        self.update()

    animatedValue = pyqtProperty(float, get_animated_value, set_animated_value)

    def set_value(self, value: float, animate: bool = True):
        self._value = max(0.0, min(100.0, value))
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._animated_value)
            self._anim.setEndValue(self._value)
            self._anim.start()
        else:
            self._animated_value = self._value
            self.update()

    def set_center_label(self, text: str, sub: str = ""):
        self._center_label = text
        self._sub_label = sub
        self.update()

    def set_compact_text(self, enabled: bool):
        self._compact_text = enabled
        self.update()

    def apply_theme(self, theme: dict):
        self._bg_color = theme.get("ring_bg", self._bg_color)
        self._color_start = theme.get("ring_start", self._color_start)
        self._color_end = theme.get("ring_end", self._color_end)
        self._glow_color = theme.get("ring_glow", self._glow_color)
        self._text_color = theme.get("text_primary", self._text_color)
        self._sub_text_color = theme.get("text_secondary", self._sub_text_color)
        self._pen_width = theme.get("ring_width", 10)
        self.update()

    # ─── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = self._pen_width + 6
        rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)
        cx, cy = w / 2, h / 2

        # ── Glow halo (subtle radial gradient behind the arc)
        if self._animated_value > 1:
            grad = QRadialGradient(cx, cy, min(w, h) / 2)
            glow = QColor(self._glow_color)
            glow.setAlpha(int(40 * self._animated_value / 100))
            grad.setColorAt(0.5, glow)
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(0, 0, w, h))

        # ── Background track ring
        pen = QPen(self._bg_color, self._pen_width, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)

        # ── Gradient foreground arc
        if self._animated_value > 0.5:
            grad = QConicalGradient(cx, cy, 90)
            grad.setColorAt(0.0, self._color_start)
            grad.setColorAt(1.0, self._color_end)
            pen = QPen(QBrush(grad), self._pen_width, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            span = int(-self._animated_value / 100.0 * 360 * 16)
            painter.drawArc(rect, 90 * 16, span)

        compact_text = self._compact_text or min(w, h) <= 100
        main_font_size = 12 if compact_text else 15
        sub_font_size = 7 if compact_text else 8
        main_rect = (
            QRectF(0, cy - 17, w, 22)
            if compact_text
            else QRectF(0, cy - 18, w, 26)
        )
        sub_rect = (
            QRectF(0, cy + 4, w, 16)
            if compact_text
            else QRectF(0, cy + 10, w, 18)
        )

        # ── Center main text
        painter.setPen(QPen(self._text_color))
        font = QFont("Segoe UI", main_font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(main_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                         self._center_label)

        # ── Sub text
        if self._sub_label:
            painter.setPen(QPen(self._sub_text_color))
            font2 = QFont("Segoe UI", sub_font_size)
            painter.setFont(font2)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                             self._sub_label)
