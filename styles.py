"""
应用样式表
提供现代化的深色强调 + 浅色背景视觉风格，参考 vtracer 官方网站配色。
"""

APP_QSS = """
* {
    font-family: 'Segoe UI', 'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif;
}

QWidget#root {
    background-color: #f5f6f8;
}

/* ===== 顶部工具栏（浅色） ===== */
QFrame#topbar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e7eb;
}
QLabel#appTitleLight {
    color: #1f2937;
    font-size: 16px;
    font-weight: 700;
}
QLabel#appSubtitleLight {
    color: #9ca3af;
    font-size: 11px;
}
QPushButton#topBtn {
    color: #4b5563;
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#topBtn:hover {
    background-color: #f3f4f6;
    border-color: #d1d5db;
}
QPushButton#topBtn:pressed {
    background-color: #e5e7eb;
}
QPushButton#topBtn:disabled {
    color: #d1d5db;
    background-color: #f9fafb;
    border-color: #e5e7eb;
}
QPushButton#primaryBtn {
    color: #ffffff;
    background-color: #6c5ce7;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #7f71ec;
}
QPushButton#primaryBtn:pressed {
    background-color: #5b4dd6;
}
QPushButton#primaryBtn:disabled {
    background-color: #b7aedc;
    color: #efeaff;
}

/* ===== 面板 ===== */
QFrame#panel {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
}
QScrollArea {
    background-color: #ffffff;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #ffffff;
}
QLabel#panelTitle {
    color: #1f2937;
    font-size: 14px;
    font-weight: 600;
}
QLabel#panelSubtitle {
    color: #9ca3af;
    font-size: 11px;
}

/* ===== 预览区 ===== */
QFrame#previewContent {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
}
QLabel#previewLabel {
    color: #6b7280;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
}
QFrame#previewBox {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
}
QLabel#emptyHint {
    color: #c7cad1;
    font-size: 14px;
}
QLabel#emptyHintIcon {
    color: #d1d5db;
    font-size: 42px;
}

/* ===== 参数 ===== */
QLabel#paramName {
    color: #374151;
    font-size: 12px;
    font-weight: 600;
}
QLabel#paramHint {
    color: #9ca3af;
    font-size: 11px;
}
QSlider::groove:horizontal {
    height: 5px;
    background: #e5e7eb;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #6c5ce7;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #7f71ec;
}
QSlider::sub-page:horizontal {
    background: #6c5ce7;
    border-radius: 2px;
}
QSpinBox {
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 5px;
    padding: 3px 6px;
    color: #1f2937;
    font-size: 12px;
    font-weight: 600;
}
QSpinBox:focus {
    border-color: #6c5ce7;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 16px;
    background: #f3f4f6;
    border: none;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #e5e7eb;
}

QRadioButton {
    color: #4b5563;
    font-size: 12px;
    spacing: 5px;
}
QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border: 2px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
}
QRadioButton::indicator:checked {
    border-color: #6c5ce7;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
        fx:0.5, fy:0.5,
        stop:0 #6c5ce7, stop:0.4 #6c5ce7,
        stop:0.5 #ffffff, stop:1 #ffffff);
}
QRadioButton:disabled {
    color: #d1d5db;
}
QRadioButton:disabled::indicator {
    border-color: #e5e7eb;
}

QPushButton#presetBtn {
    color: #4b5563;
    background-color: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 500;
}
QPushButton#presetBtn:hover {
    background-color: #e5e7eb;
}
QPushButton#presetBtn:checked {
    color: #ffffff;
    background-color: #6c5ce7;
    border-color: #6c5ce7;
}

/* ===== 分段切换按钮（ToggleGroup） ===== */
QPushButton#toggleBtn {
    color: #4b5563;
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 600;
    border-radius: 0;
}
QPushButton#toggleBtn:first-child {
    border-top-left-radius: 6px;
    border-bottom-left-radius: 6px;
}
QPushButton#toggleBtn:last-child {
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QPushButton#toggleBtn:hover {
    background-color: #f9fafb;
}
QPushButton#toggleBtn:checked {
    color: #ffffff;
    background-color: #1a2340;
    border-color: #1a2340;
}
QPushButton#toggleBtn:disabled {
    color: #d1d5db;
    background-color: #f9fafb;
}

QFrame#hline {
    color: #e5e7eb;
    background-color: #e5e7eb;
    max-height: 1px;
    border: none;
}

/* ===== 进度条 ===== */
QProgressBar {
    background-color: #f3f4f6;
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: #1f2937;
    font-size: 11px;
    font-weight: 600;
}
QProgressBar::chunk {
    background-color: #6c5ce7;
    border-radius: 5px;
}

/* ===== 底部状态栏 ===== */
QFrame#statusbar {
    background-color: #ffffff;
    border-top: 1px solid #e5e7eb;
}
QLabel#statusText {
    color: #6b7280;
    font-size: 12px;
}

/* ===== Toast 提示 ===== */
QFrame#toast {
    background-color: #1a1d29;
    border-radius: 10px;
}
QLabel#toastIcon {
    color: #34d399;
    font-size: 18px;
}
QLabel#toastText {
    color: #ffffff;
    font-size: 13px;
    font-weight: 500;
}
QLabel#toastIconError {
    color: #f87171;
    font-size: 18px;
}

/* 滚动条 */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #9ca3af;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""
