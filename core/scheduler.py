"""
GPT Usage Widget — Scheduler (Codex version)
"""
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from core.api_client import CodexAPIWorker, CodexData
from core import data_cache
from typing import Optional


class DataScheduler(QObject):
    data_updated = pyqtSignal(object)   # CodexData
    error_occurred = pyqtSignal(str)
    fetch_started = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._worker: Optional[CodexAPIWorker] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)

    def start(self):
        self._reschedule()
        if self._config.has_session_token():
            self.refresh()

    def stop(self):
        self._timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.quit()

    def refresh(self):
        token = self._config.get_session_token()
        if not token:
            self.error_occurred.emit("请先在设置中配置 Session Cookie")
            return
        if self._worker and self._worker.isRunning():
            return

        self.fetch_started.emit()
        self._worker = CodexAPIWorker(self._config)
        worker = self._worker
        worker.data_ready.connect(self._on_data)
        worker.error.connect(self.error_occurred.emit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._clear_worker)
        worker.start()

    def _on_data(self, data: CodexData):
        data_cache.save_cache(data)
        self.data_updated.emit(data)

    def _clear_worker(self):
        self._worker = None

    def set_interval(self, minutes: int):
        self._config.set("refresh_interval_minutes", minutes)
        self._reschedule()

    def _reschedule(self):
        minutes = self._config.get("refresh_interval_minutes", 5)
        self._timer.setInterval(int(minutes) * 60 * 1000)
        self._timer.start()
