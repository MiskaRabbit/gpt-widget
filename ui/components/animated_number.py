"""
GPT Usage Widget — Animated Number Label
Smoothly animates between numeric values using QVariantAnimation.
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QFont


class AnimatedLabel(QLabel):
    """A QLabel that smoothly counts from old value to new value."""

    def __init__(self, prefix: str = "", suffix: str = "", decimals: int = 2,
                 parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self._suffix = suffix
        self._decimals = decimals
        self._current: float = 0.0

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(600)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_value)

        self._update_text(0.0)

    def set_value(self, value: float, animate: bool = True):
        if animate and abs(value - self._current) > 0.001:
            self._anim.stop()
            self._anim.setStartValue(float(self._current))
            self._anim.setEndValue(float(value))
            self._anim.start()
        else:
            self._current = value
            self._update_text(value)

    def set_format(self, prefix: str = "", suffix: str = "", decimals: int = 2):
        self._prefix = prefix
        self._suffix = suffix
        self._decimals = decimals
        self._update_text(self._current)

    def _on_value(self, v):
        self._current = float(v)
        self._update_text(self._current)

    def _update_text(self, v: float):
        if self._decimals == 0:
            formatted = f"{int(v):,}"
        else:
            formatted = f"{v:,.{self._decimals}f}"
        self.setText(f"{self._prefix}{formatted}{self._suffix}")
