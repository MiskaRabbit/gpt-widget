"""
GPT Usage Widget — Entry Point (Codex version)
"""
import logging
import sys, os
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

from config.config_manager import ConfigManager
from core import data_cache
from core.scheduler import DataScheduler
from ui.widget import GPTWidget
from ui.settings_dialog import SettingsDialog
from tray.tray_icon import TrayIcon


LOG_FILE = Path.home() / ".gpt-widget" / "logs" / "app.log"


def _setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    if sys.stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    logging.info("Starting GPT Usage Widget with Python %s", sys.version)
    return LOG_FILE


def _install_excepthook():
    def handle_exception(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logging.critical("Uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = handle_exception


def main():
    _setup_logging()
    _install_excepthook()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("GPT Usage Widget")
    app.setApplicationVersion("1.1.0")
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager()
    widget = GPTWidget(config)

    scheduler = DataScheduler(config)
    scheduler.data_updated.connect(widget.update_data)
    scheduler.error_occurred.connect(widget.show_error)
    scheduler.fetch_started.connect(widget.show_fetching)

    tray = TrayIcon(widget, config, app)

    _dlg = None

    def open_settings():
        nonlocal _dlg
        if _dlg and _dlg.isVisible():
            _dlg.raise_(); return
        _dlg = SettingsDialog(config, widget)
        _dlg.settings_saved.connect(on_settings_saved)
        _dlg.show()

    def on_settings_saved():
        widget.apply_theme(config.get("theme", "dark_glass"))
        widget.apply_minimal_mode(config.get("minimal_mode", False))
        widget.setWindowOpacity(config.get("window_opacity", 92) / 100.0)
        scheduler.set_interval(config.get("refresh_interval_minutes", 5))
        if config.has_session_token():
            scheduler.refresh()

    widget.settings_requested.connect(open_settings)
    widget.refresh_requested.connect(scheduler.refresh)

    # Load cached data instantly
    cached = data_cache.load_cache()
    if cached:
        widget.update_data(cached)
    if not config.has_session_token():
        widget.show_no_token(preserve_data=bool(cached))
        QTimer.singleShot(300, open_settings)

    scheduler.start()

    if config.get("show_on_startup", True):
        widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
