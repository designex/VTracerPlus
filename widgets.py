"""
自定义控件模块
提供带标签、滑块与数值显示的参数控件，以及预设选择器等。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QSpinBox,
    QRadioButton, QButtonGroup, QFrame, QPushButton, QSizePolicy,
)


class HLine(QFrame):
    """水平分隔线。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setObjectName('hline')


class ParamSlider(QWidget):
    """带名称、提示、滑块与数值输入的复合参数控件。"""

    valueChanged = Signal(int)

    def __init__(self, name: str, hint: str, minimum: int, maximum: int,
                 default: int, parent=None):
        super().__init__(parent)
        self._name = name
        self._hint = hint
        self._minimum = minimum
        self._maximum = maximum

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 第一行：名称 + 数值（名称可换行，避免被裁剪）
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)

        self._name_label = QLabel(name)
        self._name_label.setObjectName('paramName')
        self._name_label.setWordWrap(True)
        self._name_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        top.addWidget(self._name_label, 1)

        self._spin = QSpinBox()
        self._spin.setRange(minimum, maximum)
        self._spin.setValue(default)
        self._spin.setFixedWidth(72)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._spin.valueChanged.connect(self._on_spin_changed)
        top.addWidget(self._spin)

        layout.addLayout(top)

        # 第二行：提示文字（独立一行，可换行，避免与名称挤在同一行被裁剪）
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName('paramHint')
            hint_label.setWordWrap(True)
            hint_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(hint_label)

        # 第三行：滑块
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(minimum, maximum)
        self._slider.setValue(default)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

    def _on_slider_changed(self, value: int):
        self._spin.blockSignals(True)
        self._spin.setValue(value)
        self._spin.blockSignals(False)
        self.valueChanged.emit(value)

    def _on_spin_changed(self, value: int):
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._slider.blockSignals(False)
        self.valueChanged.emit(value)

    def value(self) -> int:
        return self._spin.value()

    def set_value(self, value: int):
        self._spin.setValue(value)


class ParamRadioGroup(QWidget):
    """带名称的横向单选按钮组。"""

    valueChanged = Signal(str)

    def __init__(self, name: str, options: list, default: str, parent=None):
        """
        options: [(value, label), ...]
        """
        super().__init__(parent)
        self._options = options

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._name_label = QLabel(name)
        self._name_label.setObjectName('paramName')
        layout.addWidget(self._name_label)

        radio_row = QHBoxLayout()
        radio_row.setContentsMargins(0, 0, 0, 0)
        radio_row.setSpacing(12)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for value, label in options:
            btn = QRadioButton(label)
            btn.setProperty('value', value)
            if value == default:
                btn.setChecked(True)
            self._group.addButton(btn)
            radio_row.addWidget(btn)
        radio_row.addStretch(1)
        layout.addLayout(radio_row)

        self._group.buttonToggled.connect(self._on_toggled)

    def _on_toggled(self, button, checked):
        if checked:
            self.valueChanged.emit(button.property('value'))

    def value(self) -> str:
        btn = self._group.checkedButton()
        return btn.property('value') if btn else ''

    def set_value(self, value: str):
        for btn in self._group.buttons():
            if btn.property('value') == value:
                btn.setChecked(True)
                break

    def set_enabled(self, enabled: bool):
        for btn in self._group.buttons():
            btn.setEnabled(enabled)


class PresetButton(QPushButton):
    """预设按钮。"""

    presetClicked = Signal(str)

    def __init__(self, preset_value: str, label: str, parent=None):
        super().__init__(label, parent)
        self._preset_value = preset_value
        self.setObjectName('presetBtn')
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.presetClicked.emit(self._preset_value))

    def set_active(self, active: bool):
        self.setChecked(active)


class ToggleGroup(QWidget):
    """分段切换按钮组（类似官方 Web App 的 B/W | COLOR 风格）。

    外观：一组并排按钮，仅一个高亮，其余灰底。
    信号：valueChanged(str) —— 切换时发出当前选中值。
    """

    valueChanged = Signal(str)

    def __init__(self, options: list, default: str, parent=None):
        """
        options: [(value, label), ...]  例如 [('bw', 'B/W'), ('color', 'COLOR')]
        """
        super().__init__(parent)
        self._options = options

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btns = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, (value, label) in enumerate(options):
            btn = QPushButton(label)
            btn.setObjectName('toggleBtn')
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty('value', value)
            if value == default:
                btn.setChecked(True)
            self._group.addButton(btn)
            self._btns[value] = btn
            layout.addWidget(btn)

        self._group.buttonToggled.connect(self._on_toggled)
        # 初始化样式刷新
        self._refresh_styles()

    def _on_toggled(self, button, checked):
        if checked:
            self._refresh_styles()
            self.valueChanged.emit(button.property('value'))

    def _refresh_styles(self):
        """根据选中状态刷新各按钮样式，实现「仅高亮当前项」的视觉效果。"""
        for btn in self._group.buttons():
            if btn.isChecked():
                btn.setProperty('active', True)
            else:
                btn.setProperty('active', False)
            # 强制 Polishes 触发 QSS 重绘
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def value(self) -> str:
        btn = self._group.checkedButton()
        return btn.property('value') if btn else ''

    def set_value(self, value: str):
        for val, btn in self._btns.items():
            if val == value:
                btn.setChecked(True)
                break

    def set_enabled(self, enabled: bool):
        for btn in self._btns.values():
            btn.setEnabled(enabled)
