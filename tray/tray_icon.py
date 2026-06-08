"""
GPT Usage Widget — System Tray Icon
Provides right-click menu and balloon notifications.
"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PyQt6.QtCore import Qt, QSize


def _create_tray_icon(color: str = "#6366f1") -> QIcon:
    """Generate a simple colored circle icon programmatically."""
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Background circle
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)
    # "G" letter
    painter.setPen(QColor("white"))
    font = QFont("Segoe UI", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "G")
    painter.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, widget, config, app: QApplication, parent=None):
        super().__init__(parent)
        self._widget = widget
        self._config = config
        self._app = app

        self.setIcon(_create_tray_icon())
        self.setToolTip("GPT Usage Widget")

        self._build_menu()
        self.activated.connect(self._on_activated)

        self.show()

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: rgba(12, 12, 28, 248);
                border: 1px solid rgba(99,102,241,60);
                border-radius: 10px;
                padding: 4px;
                color: rgba(226,232,240,230);
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 12px;
            }
            QMenu::item { padding: 6px 20px 6px 12px; border-radius: 6px; }
            QMenu::item:selected { background: rgba(99,102,241,30); }
            QMenu::separator { height: 1px; background: rgba(99,102,241,25); margin: 3px 8px; }
        """)

        show_act = QAction("📊  显示窗口", self)
        show_act.triggered.connect(self._show_widget)
        menu.addAction(show_act)

        refresh_act = QAction("⟳  立即刷新", self)
        refresh_act.triggered.connect(
            lambda _checked=False: self._widget.refresh_requested.emit()
        )
        menu.addAction(refresh_act)

        settings_act = QAction("⚙  设置", self)
        settings_act.triggered.connect(
            lambda _checked=False: self._widget.settings_requested.emit()
        )
        menu.addAction(settings_act)

        menu.addSeparator()

        quit_act = QAction("✕  退出", self)
        quit_act.triggered.connect(self._app.quit)
        menu.addAction(quit_act)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_widget()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_widget()

    def _show_widget(self):
        self._widget.showNormal()
        self._widget.raise_()
        self._widget.activateWindow()

    def notify_alert(self, title: str, message: str):
        """Show a Windows balloon notification."""
        self.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )
