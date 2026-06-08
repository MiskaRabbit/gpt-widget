"""
Settings dialog for the GPT usage widget.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
)

from ui.themes import theme_manager


def _sep() -> QFrame:
    frame = QFrame()
    frame.setFrameShape(QFrame.Shape.HLine)
    frame.setStyleSheet("color: rgba(99,102,241,25); margin: 4px 0;")
    return frame


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("GPT Widget 设置")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setModal(True)
        self.setFixedWidth(460)
        self._build_ui()
        self._load_values()
        self._apply_style()

    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(24, 20, 24, 20)
        vbox.setSpacing(12)

        title = QLabel("设置")
        title.setObjectName("SettingsTitle")
        vbox.addWidget(title)
        vbox.addWidget(_sep())

        vbox.addWidget(self._section("ChatGPT Cookie（完整请求头）"))
        hint_box = QLabel(
            "获取方法：\n"
            "1. 浏览器打开 chatgpt.com 并登录\n"
            "2. 按 F12 打开 Network（网络）标签\n"
            "3. 刷新页面，点击任意 chatgpt.com 请求\n"
            "4. 在 Request Headers 中找到 Cookie 行\n"
            "5. 复制 Cookie: 后面的完整内容，粘贴到下方"
        )
        hint_box.setObjectName("HintText")
        hint_box.setWordWrap(True)
        vbox.addWidget(hint_box)

        self._cookie_edit = QTextEdit()
        self._cookie_edit.setObjectName("CookieInput")
        self._cookie_edit.setPlaceholderText(
            "__Secure-next-auth.session-token.0=eyJhb...; "
            "__Secure-next-auth.session-token.1=xxx...; "
            "cf_clearance=yyy..."
        )
        self._cookie_edit.setFixedHeight(100)
        self._cookie_edit.setAcceptRichText(False)
        vbox.addWidget(self._cookie_edit)

        self._cookie_count = QLabel("")
        self._cookie_count.setObjectName("AlertLabel")
        vbox.addWidget(self._cookie_count)
        self._cookie_edit.textChanged.connect(self._update_cookie_count)

        vbox.addWidget(_sep())
        vbox.addWidget(self._section("网络代理（可选）"))
        proxy_hint = QLabel(
            "如果浏览器能打开 ChatGPT，但这里提示网络连接失败，通常需要填写本机代理。"
        )
        proxy_hint.setObjectName("HintText")
        proxy_hint.setWordWrap(True)
        vbox.addWidget(proxy_hint)

        self._proxy_edit = QLineEdit()
        self._proxy_edit.setObjectName("SettingsInput")
        self._proxy_edit.setPlaceholderText("例如：http://127.0.0.1:7890")
        vbox.addWidget(self._proxy_edit)

        vbox.addWidget(_sep())
        vbox.addWidget(self._section("界面主题"))
        self._theme_combo = QComboBox()
        self._theme_combo.setObjectName("SettingsCombo")
        for key, info in theme_manager.THEMES.items():
            self._theme_combo.addItem(info["name"], key)
        vbox.addWidget(self._theme_combo)

        vbox.addWidget(_sep())
        vbox.addWidget(self._section("自动刷新间隔"))
        interval_row = QHBoxLayout()
        self._interval_slider = QSlider(Qt.Orientation.Horizontal)
        self._interval_slider.setObjectName("SettingsSlider")
        self._interval_slider.setRange(1, 60)
        self._interval_label = QLabel("5 分钟")
        self._interval_label.setObjectName("SliderValue")
        self._interval_label.setFixedWidth(55)
        self._interval_slider.valueChanged.connect(
            lambda value: self._interval_label.setText(f"{value} 分钟")
        )
        interval_row.addWidget(self._interval_slider)
        interval_row.addWidget(self._interval_label)
        vbox.addLayout(interval_row)

        vbox.addWidget(self._section("窗口透明度（离焦时）"))
        opacity_row = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setObjectName("SettingsSlider")
        self._opacity_slider.setRange(40, 100)
        self._opacity_label = QLabel("92%")
        self._opacity_label.setObjectName("SliderValue")
        self._opacity_label.setFixedWidth(40)
        self._opacity_slider.valueChanged.connect(
            lambda value: self._opacity_label.setText(f"{value}%")
        )
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        vbox.addLayout(opacity_row)

        vbox.addWidget(_sep())
        self._minimal_mode_cb = QCheckBox("极简模式")
        self._minimal_mode_cb.setObjectName("SettingsCheck")
        vbox.addWidget(self._minimal_mode_cb)

        self._autostart_cb = QCheckBox("开机自动启动")
        self._autostart_cb.setObjectName("SettingsCheck")
        vbox.addWidget(self._autostart_cb)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("SaveBtn")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.clicked.connect(self._save)
        save_btn.setDefault(True)

        button_row.addStretch()
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)
        vbox.addLayout(button_row)

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SettingsSection")
        return label

    def _update_cookie_count(self):
        text = self._cookie_edit.toPlainText().strip()
        if not text:
            self._cookie_count.setText("")
            return

        parts = [part.strip() for part in text.split(";") if "=" in part.strip()]
        has_session = any("session-token" in part.lower() for part in parts)
        has_cf = any("cf_clearance" in part for part in parts)

        status_parts = [f"检测到 {len(parts)} 个 cookie"]
        status_parts.append("已包含 session-token" if has_session else "缺少 session-token")
        status_parts.append("已包含 cf_clearance" if has_cf else "缺少 cf_clearance")
        self._cookie_count.setText("  |  ".join(status_parts))

    def _load_values(self):
        raw = self._config.get_raw_cookies()
        if raw:
            self._cookie_edit.setPlainText(raw)
        else:
            cookies = self._config.get_session_cookies()
            if cookies:
                parts = [f"{key}={value}" for key, value in cookies.items()]
                self._cookie_edit.setPlainText("; ".join(parts))

        theme = self._config.get("theme", "dark_glass")
        for i in range(self._theme_combo.count()):
            if self._theme_combo.itemData(i) == theme:
                self._theme_combo.setCurrentIndex(i)
                break

        self._interval_slider.setValue(self._config.get("refresh_interval_minutes", 5))
        self._opacity_slider.setValue(self._config.get("window_opacity", 92))
        self._minimal_mode_cb.setChecked(self._config.get("minimal_mode", False))
        self._autostart_cb.setChecked(self._config.get_autostart())
        self._proxy_edit.setText(self._config.get("proxy_url", ""))

    def _save(self):
        raw = self._cookie_edit.toPlainText().strip()
        if raw:
            self._config.set_raw_cookies(raw)
        else:
            self._config.clear_session_token()

        self._config.set("theme", self._theme_combo.currentData())
        self._config.set("refresh_interval_minutes", self._interval_slider.value())
        self._config.set("window_opacity", self._opacity_slider.value())
        self._config.set("minimal_mode", self._minimal_mode_cb.isChecked())
        self._config.set_proxy_url(self._proxy_edit.text())
        self._config.set_autostart(self._autostart_cb.isChecked())

        self.settings_saved.emit()
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background: rgba(10,10,26,255);
                color: rgba(226,232,240,230);
                font-family: 'Segoe UI','Microsoft YaHei';
            }
            #SettingsTitle {
                font-size:16px;
                font-weight:700;
                color:rgba(226,232,240,255);
            }
            #SettingsSection {
                font-size:11px;
                font-weight:600;
                color:rgba(99,102,241,220);
                letter-spacing:0.3px;
                margin-bottom:2px;
            }
            #HintText {
                color:rgba(100,116,139,210);
                font-size:11px;
                background:rgba(255,255,255,4);
                border:1px solid rgba(99,102,241,25);
                border-radius:8px;
                padding:8px 10px;
                line-height:1.6;
            }
            #CookieInput {
                background:rgba(255,255,255,6);
                border:1px solid rgba(99,102,241,45);
                border-radius:8px;
                color:rgba(226,232,240,230);
                font-size:11px;
                padding:7px 10px;
                font-family:'Consolas',monospace;
            }
            #SettingsInput, #SettingsCombo {
                background:rgba(255,255,255,6);
                border:1px solid rgba(99,102,241,45);
                border-radius:8px;
                color:rgba(226,232,240,230);
                padding:7px 10px;
                min-height:20px;
            }
            #SettingsCheck {
                color:rgba(226,232,240,230);
                font-size:12px;
            }
            #SettingsSlider::groove:horizontal {
                height:4px;
                background:rgba(99,102,241,30);
                border-radius:2px;
            }
            #SettingsSlider::handle:horizontal {
                background:rgba(99,102,241,255);
                width:14px;
                height:14px;
                margin:-5px 0;
                border-radius:7px;
            }
            #SliderValue {
                color:rgba(148,163,184,230);
                font-size:11px;
            }
            #AlertLabel {
                color:rgba(251,191,36,230);
                font-size:10px;
            }
            #CancelBtn, #SaveBtn {
                border-radius:8px;
                padding:7px 16px;
                font-weight:600;
            }
            #CancelBtn {
                background:rgba(255,255,255,5);
                border:1px solid rgba(148,163,184,35);
                color:rgba(148,163,184,230);
            }
            #CancelBtn:hover {
                background:rgba(255,255,255,10);
                color:rgba(226,232,240,255);
            }
            #SaveBtn {
                background:rgba(99,102,241,220);
                border:1px solid rgba(99,102,241,255);
                color:white;
            }
            #SaveBtn:hover {
                background:rgba(99,102,241,255);
            }
        """)
