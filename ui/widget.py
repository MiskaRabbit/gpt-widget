"""
GPT Usage Widget - Codex floating window.
Shows two quota rings: 5-hour quota and weekly quota.
"""
from datetime import datetime

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.api_client import CodexData
from ui.components.progress_ring import ProgressRing
from ui.themes import theme_manager


def _lbl(text: str, obj_name: str, parent=None) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(obj_name)
    return label


def _btn(text: str, obj_name: str, parent=None) -> QPushButton:
    button = QPushButton(text, parent)
    button.setObjectName(obj_name)
    button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class GPTWidget(QWidget):
    settings_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._drag_pos = QPoint()
        self._current_theme = config.get("theme", "dark_glass")
        self._is_expanded = config.get("expanded", False)
        self._minimal_mode = config.get("minimal_mode", False)

        self._normal_window_width = 300
        self._normal_ring_size = 118
        self._compact_ring_size = 96
        self._normal_ring_spacing = 14
        self._compact_ring_spacing = 8
        self._normal_ring_side_spacing = 6
        self._compact_ring_side_spacing = 0
        self._normal_container_bottom_margin = 10
        self._compact_container_bottom_margin = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._build_ui()
        self._apply_theme(self._current_theme)
        self._apply_minimal_mode_visibility()

        self.move(config.get("window_x", 60), config.get("window_y", 60))
        self.setWindowOpacity(config.get("window_opacity", 92) / 100.0)

        QTimer.singleShot(80, self._animate_show)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._container = QWidget(self)
        self._container.setObjectName("MainWidget")
        root.addWidget(self._container)

        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(
            0, 0, 0, self._normal_container_bottom_margin
        )
        self._container_layout.setSpacing(0)

        self._header_bar = self._build_header()
        self._container_layout.addWidget(self._header_bar)

        self._rings_section = self._build_rings_section()
        self._container_layout.addWidget(self._rings_section)

        self._main_divider = QWidget()
        self._main_divider.setObjectName("Divider")
        self._main_divider.setFixedHeight(1)
        self._container_layout.addWidget(self._main_divider)

        self._expand_bar = self._build_expand_bar()
        self._container_layout.addWidget(self._expand_bar)

        self._expanded_panel = self._build_expanded_panel()
        self._expand_btn.setText("▴ 收起" if self._is_expanded else "▾ 更多信息")
        self._expanded_panel.setVisible(self._is_expanded)
        self._container_layout.addWidget(self._expanded_panel)

        self._status_bar = self._build_status_bar()
        self._container_layout.addWidget(self._status_bar)

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("HeaderBar")
        bar.setFixedHeight(40)
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(14, 0, 8, 0)
        hbox.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setObjectName("MetricLabel")
        self._dot.setFixedWidth(10)
        hbox.addWidget(self._dot)

        hbox.addWidget(_lbl("Codex", "AppTitle"))

        self._plan_badge = _lbl("Plus", "PlanBadge")
        hbox.addWidget(self._plan_badge)

        self._user_lbl = _lbl("", "MetricLabel")
        self._user_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        hbox.addWidget(self._user_lbl)

        self._refresh_btn = _btn("↻", "IconButton")
        self._refresh_btn.setFixedSize(26, 26)
        self._refresh_btn.setToolTip("立即刷新")
        self._refresh_btn.clicked.connect(lambda: self.refresh_requested.emit())
        hbox.addWidget(self._refresh_btn)

        self._settings_btn = _btn("⚙", "IconButton")
        self._settings_btn.setFixedSize(26, 26)
        self._settings_btn.setToolTip("设置")
        self._settings_btn.clicked.connect(lambda: self.settings_requested.emit())
        hbox.addWidget(self._settings_btn)

        close_btn = _btn("×", "CloseButton")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("最小化到托盘")
        close_btn.clicked.connect(self.hide)
        hbox.addWidget(close_btn)
        return bar

    def _build_rings_section(self) -> QWidget:
        body = QWidget()
        self._rings_layout = QHBoxLayout(body)
        self._rings_layout.setContentsMargins(16, 16, 16, 14)
        self._rings_layout.setSpacing(self._normal_ring_spacing)

        self._period_ring_layout = QVBoxLayout()
        self._period_ring_layout.setSpacing(self._normal_ring_side_spacing)
        self._ring_period = ProgressRing()
        self._ring_period.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._ring_period.setFixedSize(self._normal_ring_size, self._normal_ring_size)
        self._ring_period.set_center_label("--", "5小时额度")
        self._period_ring_layout.addWidget(
            self._ring_period, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self._lbl_period_title = _lbl("", "SectionTitle")
        self._lbl_period_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._period_ring_layout.addWidget(self._lbl_period_title)

        self._lbl_period_detail = _lbl("", "MetricLabel")
        self._lbl_period_detail.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._period_ring_layout.addWidget(self._lbl_period_detail)
        self._rings_layout.addLayout(self._period_ring_layout)

        self._ring_divider = QWidget()
        self._ring_divider.setObjectName("Divider")
        self._ring_divider.setFixedWidth(1)
        self._rings_layout.addWidget(self._ring_divider)

        self._weekly_ring_layout = QVBoxLayout()
        self._weekly_ring_layout.setSpacing(self._normal_ring_side_spacing)
        self._ring_weekly = ProgressRing()
        self._ring_weekly.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._ring_weekly.setFixedSize(self._normal_ring_size, self._normal_ring_size)
        self._ring_weekly.set_center_label("--", "周额度")
        self._weekly_ring_layout.addWidget(
            self._ring_weekly, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self._lbl_weekly_title = _lbl("", "SectionTitle")
        self._lbl_weekly_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._weekly_ring_layout.addWidget(self._lbl_weekly_title)

        self._lbl_weekly_detail = _lbl("", "MetricLabel")
        self._lbl_weekly_detail.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._weekly_ring_layout.addWidget(self._lbl_weekly_detail)
        self._rings_layout.addLayout(self._weekly_ring_layout)
        return body

    def _build_expand_bar(self) -> QWidget:
        bar = QWidget()
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(14, 3, 14, 3)
        self._expand_btn = _btn("▾ 更多信息", "ExpandButton")
        self._expand_btn.setFixedHeight(20)
        self._expand_btn.clicked.connect(self._toggle_expand)
        hbox.addWidget(self._expand_btn)
        return bar

    def _build_expanded_panel(self) -> QWidget:
        panel = QWidget()
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(16, 8, 16, 4)
        vbox.setSpacing(6)

        vbox.addWidget(_lbl("账户信息", "SectionTitle"))

        self._info_rows: list[tuple[QLabel, QLabel]] = []
        for label_text in ("邮箱", "套餐", "Session 有效期", "数据来源"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            key_label = _lbl(label_text, "ModelName")
            key_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            key_label.setFixedWidth(90)

            value_label = _lbl("—", "ModelCost")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            value_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )

            row_layout.addWidget(key_label)
            row_layout.addWidget(value_label)
            vbox.addWidget(row)
            self._info_rows.append((key_label, value_label))
        return panel

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(14, 2, 14, 0)

        self._status_lbl = _lbl("等待数据…", "StatusBar")
        hbox.addWidget(self._status_lbl)
        hbox.addStretch()

        self._time_lbl = _lbl("", "StatusBar")
        hbox.addWidget(self._time_lbl)
        return bar

    def update_data(self, data: CodexData):
        self._ring_period.set_value(data.period_percent)
        self._ring_period.set_center_label(f"{data.period_percent:.0f}%", "5小时额度")
        self._lbl_period_detail.setText("")

        self._ring_weekly.set_value(data.weekly_percent)
        self._ring_weekly.set_center_label(f"{data.weekly_percent:.0f}%", "周额度")
        self._lbl_weekly_detail.setText("")

        self._user_lbl.setText(data.user_name[:16] if data.user_name else "")
        self._plan_badge.setText(data.plan[:12] if data.plan else "Plus")

        expires_display = data.session_expires[:10] if data.session_expires else "未知"
        info_values = [
            data.user_email or "—",
            data.plan,
            expires_display,
            data.data_source or "—",
        ]
        for i, (_, value_label) in enumerate(self._info_rows):
            if i < len(info_values):
                value_label.setText(info_values[i])

        now = datetime.now().strftime("%H:%M")
        self._set_status("已更新", error=False)
        self._time_lbl.setText(now)
        self._dot.setStyleSheet("color: #22c55e;")
        self.adjustSize()

    def show_error(self, msg: str):
        self._set_status(msg, error=True)
        self._dot.setStyleSheet("color: #ef4444;")

    def show_fetching(self):
        self._set_status("获取数据中…", error=False)
        self._dot.setStyleSheet("color: #f59e0b;")

    def show_no_token(self, preserve_data: bool = False):
        self._set_status("请在设置中配置 Session Cookie", error=True)
        if not preserve_data:
            self._ring_period.set_value(0, animate=False)
            self._ring_period.set_center_label("--", "5小时额度")
            self._ring_weekly.set_value(0, animate=False)
            self._ring_weekly.set_center_label("--", "周额度")
            self._lbl_period_detail.setText("")
            self._lbl_weekly_detail.setText("")
        self._dot.setStyleSheet("color: #64748b;")

    def _set_status(self, text: str, error: bool = False):
        self.setToolTip(text)
        self._status_lbl.setText(text)
        self._status_lbl.setToolTip(text)
        self._status_lbl.setProperty("error", "true" if error else "false")
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

    def _toggle_expand(self):
        self._is_expanded = not self._is_expanded
        self._config.set("expanded", self._is_expanded)
        self._expanded_panel.setVisible(self._is_expanded and not self._minimal_mode)
        self._expand_btn.setText("▴ 收起" if self._is_expanded else "▾ 更多信息")
        self.adjustSize()

    def apply_theme(self, name: str):
        self._current_theme = name
        self._config.set("theme", name)
        self._apply_theme(name)

    def _apply_theme(self, name: str):
        qss = theme_manager.load_qss(name)
        self._container.setStyleSheet(qss)

        colors = theme_manager.get_theme(name)
        self._ring_period.apply_theme(colors)

        weekly_colors = dict(colors)
        weekly_colors["ring_start"] = colors.get("ring_end", colors.get("ring_start"))
        weekly_colors["ring_end"] = colors.get("ring_start", colors.get("ring_end"))
        self._ring_weekly.apply_theme(weekly_colors)

    def apply_minimal_mode(self, enabled: bool):
        self._minimal_mode = bool(enabled)
        self._config.set("minimal_mode", self._minimal_mode)
        self._apply_minimal_mode_visibility()

    def _set_ring_sizes(self, size: int):
        self._ring_period.setFixedSize(size, size)
        self._ring_weekly.setFixedSize(size, size)

    def _set_ring_compact_text(self, enabled: bool):
        self._ring_period.set_compact_text(enabled)
        self._ring_weekly.set_compact_text(enabled)

    def _apply_minimal_mode_visibility(self):
        show_full = not self._minimal_mode

        self._header_bar.setVisible(show_full)
        self._main_divider.setVisible(show_full)
        self._expand_bar.setVisible(show_full)
        self._status_bar.setVisible(show_full)
        self._expanded_panel.setVisible(show_full and self._is_expanded)

        self._lbl_period_title.setVisible(False)
        self._lbl_period_detail.setVisible(False)
        self._lbl_weekly_title.setVisible(False)
        self._lbl_weekly_detail.setVisible(False)

        if self._minimal_mode:
            self._container_layout.setContentsMargins(
                0, 0, 0, self._compact_container_bottom_margin
            )
            self._rings_layout.setContentsMargins(8, 8, 8, 8)
            self._rings_layout.setSpacing(self._compact_ring_spacing)
            self._period_ring_layout.setSpacing(self._compact_ring_side_spacing)
            self._weekly_ring_layout.setSpacing(self._compact_ring_side_spacing)
            self._set_ring_sizes(self._compact_ring_size)
            self._set_ring_compact_text(True)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        else:
            self._container_layout.setContentsMargins(
                0, 0, 0, self._normal_container_bottom_margin
            )
            self._rings_layout.setContentsMargins(16, 16, 16, 14)
            self._rings_layout.setSpacing(self._normal_ring_spacing)
            self._period_ring_layout.setSpacing(self._normal_ring_side_spacing)
            self._weekly_ring_layout.setSpacing(self._normal_ring_side_spacing)
            self._set_ring_sizes(self._normal_ring_size)
            self._set_ring_compact_text(False)
            self.setMinimumWidth(self._normal_window_width)
            self.setMaximumWidth(self._normal_window_width)

        self._container_layout.activate()
        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        pos = self.pos()
        self._config.set("window_x", pos.x())
        self._config.set("window_y", pos.y())
        self._drag_pos = QPoint()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(12,12,28,245);
                border: 1px solid rgba(99,102,241,60);
                border-radius: 10px; padding: 4px;
                color: rgba(226,232,240,230);
                font-family: 'Segoe UI'; font-size: 12px;
            }
            QMenu::item { padding: 5px 20px 5px 12px; border-radius: 6px; }
            QMenu::item:selected { background: rgba(99,102,241,30); }
            QMenu::separator { height:1px; background:rgba(99,102,241,25); margin:3px 8px; }
        """)

        menu.addAction("↻ 立即刷新").triggered.connect(
            lambda _checked=False: self.refresh_requested.emit()
        )
        menu.addSeparator()

        minimal_act = menu.addAction("极简模式")
        minimal_act.setCheckable(True)
        minimal_act.setChecked(self._minimal_mode)
        minimal_act.toggled.connect(self.apply_minimal_mode)
        menu.addSeparator()

        theme_menu = QMenu("切换主题", self)
        theme_menu.setStyleSheet(menu.styleSheet())
        for key, info in theme_manager.THEMES.items():
            prefix = "✓ " if key == self._current_theme else "  "
            act = theme_menu.addAction(prefix + info["name"])
            act.triggered.connect(lambda _checked=False, k=key: self.apply_theme(k))
        menu.addMenu(theme_menu)

        menu.addAction("设置").triggered.connect(
            lambda _checked=False: self.settings_requested.emit()
        )
        menu.addSeparator()
        menu.addAction("最小化到托盘").triggered.connect(self.hide)
        menu.addAction("退出").triggered.connect(
            lambda _checked=False: QApplication.instance().quit()
        )
        menu.exec(event.globalPos())

    def enterEvent(self, event):
        self.setWindowOpacity(1.0)

    def leaveEvent(self, event):
        self.setWindowOpacity(self._config.get("window_opacity", 92) / 100.0)

    def _animate_show(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(400)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.setGraphicsEffect(None))
        anim.start()
