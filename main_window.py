"""
主窗口模块
整合图片上传、预览、参数设置、转换进度、Toast 提示与 SVG 保存等全部交互。
"""

import os
import re
import sys
import shutil
import tempfile
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QRectF, QSize, Signal
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QDragEnterEvent, QDropEvent,
    QFont, QIcon, QPalette, QBrush, QLinearGradient,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFileDialog, QProgressBar, QFrame, QScrollArea,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QSizePolicy,
    QStackedWidget, QApplication, QSpacerItem, QSplitter,
)
from PySide6.QtSvg import QSvgRenderer

from converter import ConversionParams, ConversionWorker, get_vtracer_path
from widgets import HLine, ParamSlider, ToggleGroup
from styles import APP_QSS


SUPPORTED_IMAGE_FILTER = '图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;所有文件 (*.*)'


def make_checkerboard_pixmap(w: int, h: int, cell: int = 12) -> QPixmap:
    """生成棋盘格透明背景图。"""
    pm = QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setPen(Qt.PenStyle.NoPen)
    light = QColor('#ffffff')
    dark = QColor('#eef0f3')
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            c = light if ((x // cell) + (y // cell)) % 2 == 0 else dark
            painter.fillRect(x, y, cell, cell, c)
    painter.end()
    return pm


class ImagePreview(QFrame):
    """图片预览框：支持原图位图与 SVG 矢量图两种模式，支持缩放、拖拽与点击上传。"""

    imageClicked = Signal()       # 点击预览区域（仅非 SVG 模式）
    imageDropped = Signal(str)    # 拖拽文件路径

    def __init__(self, title: str, is_svg: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName('previewBox')
        self.setAcceptDrops(True)
        self._is_svg = is_svg
        self._title = title
        self._pixmap = None
        self._svg_path = None
        self._min_size = 280

        # 内容容器
        content = QFrame()
        content.setObjectName('previewContent')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 标题栏
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(12, 8, 12, 4)
        self._title_label = QLabel(title)
        self._title_label.setObjectName('previewLabel')
        title_bar.addWidget(self._title_label)
        title_bar.addStretch(1)
        self._info_label = QLabel('')
        self._info_label.setObjectName('previewLabel')
        title_bar.addWidget(self._info_label)
        content_layout.addLayout(title_bar)

        # 内容区
        self._stack = QStackedWidget()

        # 空状态
        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setContentsMargins(0, 0, 0, 0)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label = QLabel('🖼' if not is_svg else '✦')
        icon_label.setObjectName('emptyHintIcon')
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_text = '点击或拖拽图片到此处' if not is_svg else '转换完成后\n矢量图将显示在此'
        hint_label = QLabel(hint_text)
        hint_label.setObjectName('emptyHint')
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(icon_label)
        el.addSpacing(8)
        el.addWidget(hint_label)
        self._empty_index = self._stack.addWidget(empty)

        # 图片显示
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._image_index = self._stack.addWidget(self._image_label)

        content_layout.addWidget(self._stack, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(content)

        self.setMinimumSize(self._min_size, self._min_size)

        # ---- 点击上传（仅原图预览） ----
    def mousePressEvent(self, event):
        if not self._is_svg and event.button() == Qt.MouseButton.LeftButton:
            self.imageClicked.emit()
        super().mousePressEvent(event)

    # ---- 拖拽 ----
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and self._is_image_url(urls[0]):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not self._is_svg and event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if path and self._is_image_path(path):
                self.imageDropped.emit(path)
                event.acceptProposedAction()

    @staticmethod
    def _is_image_url(url) -> bool:
        return ImagePreview._is_image_path(url.toLocalFile())

    @staticmethod
    def _is_image_path(path: str) -> bool:
        if not path:
            return False
        ext = os.path.splitext(path)[1].lower()
        return ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff'}

    # ---- 显示 ----
    def set_image(self, path: str):
        """显示位图。"""
        self._svg_path = None
        pm = QPixmap(path)
        if pm.isNull():
            self.show_empty()
            return
        self._pixmap = pm
        self._render_pixmap()
        try:
            size = os.path.getsize(path) / 1024
            self._info_label.setText(f'{pm.width()}×{pm.height()}  ·  {size:.0f} KB')
        except OSError:
            self._info_label.setText(f'{pm.width()}×{pm.height()}')
        self._stack.setCurrentIndex(self._image_index)

    @staticmethod
    def _detect_svg_bg_color(svg_path: str) -> QColor:
        """解析 SVG 文件，智能检测合适的预览背景色。

        策略：统计所有 path 的 fill 色，取出现频率最高的颜色作为「背景色」，
        并根据其亮度决定画布填充色：
          - 若背景色偏暗（亮度 < 128）→ 画布用 #ffffff（白底），确保深色前景可见
          - 若背景色偏亮 → 画布用该背景色本身（保持原有行为）
        这样无论原图是黑底白字还是白底黑字，预览都能正确显示。
        """
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()
            colors = re.findall(r'<path[^>]*fill="(#[0-9A-Fa-f]{6})"', content)
            if not colors:
                return Qt.GlobalColor.transparent
            # 统计出现次数最多的颜色（视为背景/主色）
            from collections import Counter
            most_common = Counter(colors).most_common(1)[0][0]
            bg = QColor(most_common)
            # 感知亮度公式 (Rec. 601)
            brightness = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
            if brightness < 128:
                return QColor('#ffffff')   # 暗色背景图 → 用白底渲染
            return bg                      # 亮色背景图 → 用原色
        except OSError:
            return Qt.GlobalColor.transparent

    def set_svg(self, path: str):
        """渲染并显示 SVG。自动检测背景色填充以避免镂空/透明问题。"""
        if not os.path.exists(path):
            self.show_empty()
            return
        self._svg_path = path
        renderer = QSvgRenderer(path)
        if not renderer.isValid():
            self.show_empty()
            return

        # 默认渲染尺寸为 SVG 自带 viewBox，最大限制 2048
        vb = renderer.viewBoxF()
        w = int(vb.width()) if vb.width() > 0 else 800
        h = int(vb.height()) if vb.height() > 0 else 600
        scale = min(1.0, 2048 / max(w, h))
        rw, rh = max(1, int(w * scale)), max(1, int(h * scale))

        img = QImage(rw, rh, QImage.Format.Format_ARGB32)

        # 智能检测背景色：解析 SVG 第一个（通常为全画布背景）path 的 fill 色
        bg_color = self._detect_svg_bg_color(path)
        img.fill(bg_color)

        painter = QPainter(img)
        renderer.render(painter, QRectF(0, 0, rw, rh))
        painter.end()

        self._pixmap = QPixmap.fromImage(img)
        self._render_pixmap()
        try:
            size = os.path.getsize(path) / 1024
            self._info_label.setText(f'{w}×{h}  ·  SVG {size:.0f} KB')
        except OSError:
            self._info_label.setText(f'{w}×{h}')
        self._stack.setCurrentIndex(self._image_index)

    def _render_pixmap(self):
        """根据控件尺寸缩放显示当前 pixmap。"""
        if self._pixmap is None or self._pixmap.isNull():
            return
        avail = self._image_label.size()
        if avail.width() < 10 or avail.height() < 10:
            avail = QSize(self._min_size - 24, self._min_size - 24)
        scaled = self._pixmap.scaled(
            avail, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        # 合成棋盘格背景以体现透明区域
        canvas = make_checkerboard_pixmap(scaled.width(), scaled.height())
        p2 = QPainter(canvas)
        p2.drawPixmap(0, 0, scaled)
        p2.end()
        self._image_label.setPixmap(canvas)

    def show_empty(self):
        self._pixmap = None
        self._svg_path = None
        self._info_label.setText('')
        self._stack.setCurrentIndex(self._empty_index)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._stack.currentIndex() == self._image_index:
            QTimer.singleShot(0, self._render_pixmap)

    def get_svg_path(self):
        return self._svg_path


class Toast(QFrame):
    """浮层 Toast 提示，自动淡出。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('toast')
        self.setFixedHeight(48)
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        self._icon = QLabel('✓')
        self._icon.setObjectName('toastIcon')
        layout.addWidget(self._icon)

        self._text = QLabel('')
        self._text.setObjectName('toastText')
        layout.addWidget(self._text, 1)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_success(self, text: str, duration: int = 3000):
        self._icon.setText('✓')
        self._icon.setObjectName('toastIcon')
        self._icon.setStyle(self._icon.style())
        self._text.setText(text)
        self._reposition()
        self.show()
        self._timer.start(duration)

    def show_error(self, text: str, duration: int = 4000):
        self._icon.setText('✕')
        self._icon.setObjectName('toastIconError')
        self._icon.setStyle(self._icon.style())
        self._text.setText(text)
        self._reposition()
        self.show()
        self._timer.start(duration)

    def _reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        pw = parent.width()
        w = max(self.sizeHint().width(), 260)
        self.setFixedWidth(w)
        self.move((pw - w) // 2, 24)


class ParamPanel(QFrame):
    """参数设置面板 —— 参考 vtracer 官方 Web App 布局。

    布局结构：
      ┌─ Clustering · 聚类 ─────────────────────┐
      │                    [B/W] [COLOR]         │
      │              [CUTOUT] [STACKED]  (仅COLOR)│
      │  Filter Speckle (Cleaner)   4  ●━━━       │
      │  Color Precision (More acc) 6  ●━━━ (仅COLOR)│
      │  Gradient Step (Less layers) 16 ●━ (仅COLOR) │
      ├─ Curve Fitting · 曲线拟合 ────────────┤
      │        [PIXEL] [POLYGON] [SPLINE]     │
      │  Corner Threshold (Smoother) 60  ●━━━   │
      │  Segment Length (More coarse) 4  ●━━━   │
      │  Splice Threshold (Less acc)  45  ●━━━   │
      └────────────────────────────────────────┘

    B/W 模式下隐藏：hierarchical / color_precision / gradient_step
    COLOR 模式下显示全部参数。
    Path Precision 不暴露在 UI 中（使用内部默认值 10）。
    """

    paramsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('panel')
        self._building = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        # 标题
        title = QLabel('转换参数')
        title.setObjectName('panelTitle')
        outer.addWidget(title)
        sub = QLabel('根据图片情况调整参数，点击"开始转换"可以查看结果')
        sub.setObjectName('panelSubtitle')
        outer.addWidget(sub)

        # ===== 滚动区域 =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 4, 0)
        cl.setSpacing(12)

        # ══════════════════════════════════
        # Clustering 区域
        # ══════════════════════════════════
        cluster_header = QHBoxLayout()
        cluster_header.setSpacing(0)
        cluster_label = QLabel('聚类参数')
        cluster_label.setObjectName('paramName')
        cluster_header.addWidget(cluster_label)
        cluster_header.addStretch(1)
        cl.addLayout(cluster_header)

        # B/W | COLOR 切换按钮组
        self._color_mode = ToggleGroup(
            [('bw', '黑白'), ('color', '彩色')], 'bw')
        self._color_mode.valueChanged.connect(self._on_color_mode_changed)
        cl.addWidget(self._color_mode)

        # CUTOUT | STACKED （仅 COLOR 模式显示）
        self._hierarchical_container = QWidget()
        h_layout = QHBoxLayout(self._hierarchical_container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        self._hierarchical = ToggleGroup(
            [('cutout', '抠图'), ('stacked', '堆叠')], 'stacked')
        self._hierarchical.valueChanged.connect(self._on_changed)
        h_layout.addWidget(self._hierarchical)
        h_layout.addStretch(1)
        cl.addWidget(self._hierarchical_container)

        # Filter Speckle
        self._filter_speckle = ParamSlider(
            '去噪强度', '(越干净)', 0, 16, 4)
        self._filter_speckle.valueChanged.connect(self._on_changed)
        cl.addWidget(self._filter_speckle)

        # Color Precision （仅 COLOR 模式）
        self._color_precision = ParamSlider(
            '色彩精度', '(越高越准)', 1, 8, 6)
        self._color_precision.valueChanged.connect(self._on_changed)
        cl.addWidget(self._color_precision)

        # Gradient Step （仅 COLOR 模式）
        self._gradient_step = ParamSlider(
            '渐变层级', '(层数越少)', 1, 128, 16)
        self._gradient_step.valueChanged.connect(self._on_changed)
        cl.addWidget(self._gradient_step)

        # 分隔线
        cl.addWidget(HLine())

        # ══════════════════════════════════
        # Curve Fitting 区域
        # ══════════════════════════════════
        curve_header = QHBoxLayout()
        curve_header.setSpacing(0)
        curve_label = QLabel('曲线拟合参数')
        curve_label.setObjectName('paramName')
        curve_header.addWidget(curve_label)
        curve_header.addStretch(1)
        cl.addLayout(curve_header)

        # PIXEL | POLYGON | SPLINE 切换
        self._mode = ToggleGroup(
            [('pixel', '像素'), ('polygon', '多边形'), ('spline', '样条')], 'spline')
        self._mode.valueChanged.connect(self._on_changed)
        cl.addWidget(self._mode)

        # Corner Threshold
        self._corner_threshold = ParamSlider(
            '拐点阈值', '(越平滑)', 0, 180, 60)
        self._corner_threshold.valueChanged.connect(self._on_changed)
        cl.addWidget(self._corner_threshold)

        # Segment Length
        self._segment_length = ParamSlider(
            '线段长度', '(更粗糙)', 1, 64, 4)
        self._segment_length.valueChanged.connect(self._on_changed)
        cl.addWidget(self._segment_length)

        # Splice Threshold
        self._splice_threshold = ParamSlider(
            '拼接阈值', '(越精确)', 0, 90, 45)
        self._splice_threshold.valueChanged.connect(self._on_changed)
        cl.addWidget(self._splice_threshold)

        cl.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._building = False

        # 初始化：按默认 B/W 模式隐藏 color-only 参数
        self._update_color_mode_ui()

    def _on_color_mode_changed(self, value: str):
        """色彩模式切换时，更新 UI 显示/隐藏。"""
        if self._building:
            return
        self._update_color_mode_ui()
        self.paramsChanged.emit()

    def _update_color_mode_ui(self):
        """根据当前色彩模式，显示或隐藏 color-only 参数。

        COLOR 模式：显示 hierarchical / color_precision / gradient_step
        B/W 模式：隐藏以上三项
        """
        is_color = self._color_mode.value() == 'color'
        self._hierarchical_container.setVisible(is_color)
        self._color_precision.setVisible(is_color)
        self._gradient_step.setVisible(is_color)

    def _on_changed(self, *_):
        if self._building:
            return
        self.paramsChanged.emit()

    def get_params(self) -> ConversionParams:
        return ConversionParams(
            color_mode=self._color_mode.value(),
            hierarchical=self._hierarchical.value(),
            filter_speckle=self._filter_speckle.value(),
            color_precision=self._color_precision.value(),
            gradient_step=self._gradient_step.value(),
            mode=self._mode.value(),
            corner_threshold=self._corner_threshold.value(),
            segment_length=self._segment_length.value(),
            splice_threshold=self._splice_threshold.value(),
            path_precision=10,           # 内部固定值，不暴露在 UI
            preset=None,                # 无预设系统
        )

    def reset_to_defaults(self):
        """重置所有参数为推荐默认值。"""
        self._building = True
        # Clustering 默认
        self._color_mode.set_value('bw')
        self._hierarchical.set_value('stacked')
        self._filter_speckle.set_value(4)
        self._color_precision.set_value(6)
        self._gradient_step.set_value(16)
        # Curve Fitting 默认
        self._mode.set_value('spline')
        self._corner_threshold.set_value(60)
        self._segment_length.set_value(4)
        self._splice_threshold.set_value(45)
        self._building = False
        self._update_color_mode_ui()
        self.paramsChanged.emit()


class MainWindow(QMainWindow):
    """应用主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('VTracer Plus v0.6.4 · 20260622 by Alex')
        self.resize(1280, 820)
        self.setMinimumSize(1080, 640)
        self.setAcceptDrops(True)

        # 设置应用图标
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base, 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._input_path = None
        self._output_svg = None
        self._worker = None
        self._temp_dir = tempfile.mkdtemp(prefix='vtraceplus_')

        self._build_ui()
        self._wire_signals()
        self._update_button_states()

    # ===== UI 构建 =====
    def _build_ui(self):
        root = QWidget()
        root.setObjectName('root')
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 顶部栏 ----
        topbar = QFrame()
        topbar.setObjectName('topbar')
        topbar.setFixedHeight(72)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(20, 10, 12, 10)
        tb_layout.setSpacing(16)

        # 标题区（仅副标题说明文字，2行排版）
        subtitle = QLabel(
            '软件使用注意事项：上传的原图请选择黑白风格或者大色块的图片，尽量不要出现渐变色，过于复杂偏写实的图，可以借助AI工具生成或者风格转绘后再使用工具转换。\n'
            '本工具基于visioncortex VTracer开源项目进行二次开发，完全免费。')
        subtitle.setObjectName('appSubtitleLight')
        subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb_layout.addWidget(subtitle)

        self._upload_btn = QPushButton('📤  上传图片')
        self._upload_btn.setObjectName('topBtn')
        self._upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tb_layout.addWidget(self._upload_btn)

        self._reset_btn = QPushButton('↻  重新开始')
        self._reset_btn.setObjectName('topBtn')
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tb_layout.addWidget(self._reset_btn)

        layout.addWidget(topbar)

        # ---- 主体三栏（使用 QSplitter 以便用户可拖拽调整各栏宽度） ----
        body_container = QWidget()
        body_outer = QVBoxLayout(body_container)
        body_outer.setContentsMargins(16, 16, 16, 12)
        body_outer.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName('bodySplitter')
        splitter.setHandleWidth(10)
        splitter.setChildrenCollapsible(False)
        self._splitter = splitter

        # 左：原图预览
        self._original_preview = ImagePreview('ORIGINAL · 原图', is_svg=False)
        self._original_preview.setMinimumWidth(280)

        # 中：矢量图预览
        self._svg_preview = ImagePreview('VECTORIZED · 矢量图', is_svg=True)
        self._svg_preview.setMinimumWidth(280)

        # 右：参数面板（最小宽度 360，可向右拖拽放大）
        self._param_panel = ParamPanel()
        self._param_panel.setMinimumWidth(360)

        splitter.addWidget(self._original_preview)
        splitter.addWidget(self._svg_preview)
        splitter.addWidget(self._param_panel)

        # 初始比例：原图 : 矢量图 : 参数 = 1 : 1 : 0（参数固定 360 起步）
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([424, 424, 360])

        # 尝试恢复上次保存的比例
        try:
            from PySide6.QtCore import QSettings
            settings = QSettings('VTracerPlus', 'VTracerPlus')
            saved = settings.value('splitter/sizes')
            if saved:
                splitter.restoreState(saved)
        except Exception:  # noqa: BLE001
            pass

        # 让分隔条样式更明显
        splitter.setStyleSheet(
            'QSplitter::handle { background-color: transparent; }'
            'QSplitter::handle:horizontal { width: 10px; }'
        )

        body_outer.addWidget(splitter)
        layout.addWidget(body_container, 1)

        # ---- 底部状态栏 ----
        statusbar = QFrame()
        statusbar.setObjectName('statusbar')
        statusbar.setFixedHeight(60)
        sb_layout = QHBoxLayout(statusbar)
        sb_layout.setContentsMargins(20, 10, 20, 10)
        sb_layout.setSpacing(14)

        self._status_text = QLabel('准备就绪 · 请上传一张图片开始')
        self._status_text.setObjectName('statusText')
        sb_layout.addWidget(self._status_text)

        sb_layout.addStretch(1)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(220)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat('就绪')
        sb_layout.addWidget(self._progress)

        self._convert_btn = QPushButton('⚡  开始转换')
        self._convert_btn.setObjectName('primaryBtn')
        self._convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._convert_btn.setEnabled(False)
        sb_layout.addWidget(self._convert_btn)

        self._save_btn = QPushButton('💾  保存 SVG')
        self._save_btn.setObjectName('topBtn')
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setEnabled(False)
        sb_layout.addWidget(self._save_btn)

        layout.addWidget(statusbar)

        # Toast
        self._toast = Toast(root)

    def _wire_signals(self):
        self._upload_btn.clicked.connect(self._on_upload)
        self._reset_btn.clicked.connect(self._on_reset)
        self._convert_btn.clicked.connect(self._on_convert)
        self._save_btn.clicked.connect(self._on_save)
        self._original_preview.imageDropped.connect(self._load_image)
        self._original_preview.imageClicked.connect(self._on_upload)

    # ===== 槽函数 =====
    def _on_upload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择图片', '', SUPPORTED_IMAGE_FILTER)
        if path:
            self._load_image(path)

    def _load_image(self, path: str):
        if not os.path.exists(path):
            self._toast.show_error('文件不存在')
            return
        self._input_path = path
        self._output_svg = None
        self._original_preview.set_image(path)
        self._svg_preview.show_empty()
        self._progress.setValue(0)
        self._progress.setFormat('就绪')
        self._status_text.setText(f'已加载：{os.path.basename(path)}  ·  点击"开始转换"生成矢量图')
        self._convert_btn.setEnabled(True)
        self._save_btn.setEnabled(False)
        self._toast.show_success(f'图片已加载：{os.path.basename(path)}')

    def _on_reset(self):
        self._input_path = None
        self._output_svg = None
        self._original_preview.show_empty()
        self._svg_preview.show_empty()
        self._progress.setValue(0)
        self._progress.setFormat('就绪')
        self._status_text.setText('准备就绪 · 请上传一张图片开始')
        self._convert_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        # 重置参数面板到默认值，并切换回「自定义」预设
        self._param_panel.reset_to_defaults()
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.terminate()
        self._toast.show_success('已重置，可重新上传图片')

    def _on_convert(self):
        if not self._input_path:
            self._toast.show_error('请先上传图片')
            return
        if self._worker and self._worker.isRunning():
            self._toast.show_error('正在转换中，请稍候…')
            return

        # 准备输出路径
        base = os.path.splitext(os.path.basename(self._input_path))[0]
        timestamp = datetime.now().strftime('%H%M%S')
        out_name = f'{base}_{timestamp}.svg'
        out_path = os.path.join(self._temp_dir, out_name)

        params = self._param_panel.get_params()

        self._convert_btn.setEnabled(False)
        self._upload_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._progress.setValue(0)
        self._progress.setFormat('转换中…')
        self._status_text.setText('正在矢量化，请稍候…')

        self._worker = ConversionWorker(self._input_path, out_path, params, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, pct: int, text: str):
        self._progress.setValue(pct)
        self._progress.setFormat(f'{pct}%')
        self._status_text.setText(text)

    def _on_finished(self, svg_path: str):
        self._output_svg = svg_path
        self._svg_preview.set_svg(svg_path)
        self._progress.setValue(100)
        self._progress.setFormat('完成 100%')
        self._status_text.setText('✓ 转换完成！可点击"保存 SVG"导出到本地')
        self._convert_btn.setEnabled(True)
        self._upload_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._toast.show_success('矢量图转换完成！')

    def _on_failed(self, msg: str):
        self._progress.setValue(0)
        self._progress.setFormat('失败')
        self._status_text.setText(f'✕ {msg}')
        self._convert_btn.setEnabled(True)
        self._upload_btn.setEnabled(True)
        self._toast.show_error(msg)

    def _on_save(self):
        if not self._output_svg or not os.path.exists(self._output_svg):
            self._toast.show_error('没有可保存的矢量图')
            return

        base = os.path.splitext(os.path.basename(self._input_path))[0] if self._input_path else 'output'
        default_name = f'{base}.svg'
        path, _ = QFileDialog.getSaveFileName(
            self, '保存 SVG 文件', default_name, 'SVG 矢量图 (*.svg)')
        if not path:
            return
        if not path.lower().endswith('.svg'):
            path += '.svg'
        try:
            shutil.copy2(self._output_svg, path)
            self._toast.show_success(f'已保存到：{os.path.basename(path)}')
            self._status_text.setText(f'✓ 已保存：{path}')
        except Exception as e:  # noqa: BLE001
            self._toast.show_error(f'保存失败：{e}')

    def _update_button_states(self):
        has_input = self._input_path is not None
        self._convert_btn.setEnabled(has_input and not (self._worker and self._worker.isRunning()))
        self._save_btn.setEnabled(self._output_svg is not None)

    # ===== 窗口事件 =====
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_toast'):
            self._toast._reposition()

    def closeEvent(self, event):
        # 保存 splitter 比例到配置目录，便于下次启动恢复
        try:
            if hasattr(self, '_splitter'):
                from PySide6.QtCore import QSettings
                settings = QSettings('VTracerPlus', 'VTracerPlus')
                settings.setValue('splitter/sizes', self._splitter.saveState())
        except Exception:  # noqa: BLE001
            pass
        # 清理临时目录
        try:
            if self._worker and self._worker.isRunning():
                self._worker.cancel()
                self._worker.wait(2000)
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
        event.accept()
