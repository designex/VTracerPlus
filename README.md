# VTracer Plus · 位图转矢量图桌面工具

基于开源项目 [visioncortex/vtracer](https://github.com/visioncortex/vtracer) v0.6.4 二次开发的 Windows 本地桌面应用，可将 PNG / JPG / BMP / GIF / WEBP / TIFF 等位图转换为 SVG 矢量图。

<img width="1407" height="852" alt="111530d6ea31a426f59283a072baed4c" src="https://github.com/user-attachments/assets/54d0394e-bd8a-46de-9394-aa9ef8ad0d41" />

## ✨ 功能特性

- **图片上传**：点击按钮或直接拖拽图片到窗口即可加载
- **双图预览**：左侧原图、右侧矢量图同屏对比（带透明棋盘格背景）
- **智能背景渲染**：自动检测 SVG 主色亮度，黑底白字图自动用白底渲染
- **参数调节**：完整覆盖 vtracer 官方 Web 应用的全部参数
  - **聚类参数**：色彩模式（黑白 · 彩色）、层级聚类（抠图 · 堆叠）、去噪强度、色彩精度、渐变层级
  - **曲线拟合参数**：拟合模式（像素 · 多边形 · 样条）、拐点阈值、线段长度、拼接阈值
- **分段切换控件**：ToggleGroup 风格与官方 Web App 对齐
- **条件显示**：黑白模式自动隐藏彩色专属参数
- **转换进度条**：实时显示转换进度百分比与状态文本
- **Toast 提示**：浮层即时反馈转换结果
- **重新开始**：一键清空状态、重新上传图片
- **保存 SVG**：将矢量图导出到任意本地路径
- **QSplitter 可拖拽布局**：三栏宽度可自由调整，比例自动记忆

## 📦 直接使用

1. 进入 `dist/` 目录
2. 双击运行 `VTracerPlus.exe`（无需安装 Python 或任何依赖，单文件即可运行，约 45 MB）
3. 上传图片 → 调整参数 → 点击「开始转换」→ 保存 SVG

> 首次启动可能需要数秒（正在解压内嵌资源）。程序已内嵌 `vtracer.exe`，无需额外下载。

## 🛠 开发环境

### 依赖

- Python 3.13+
- PySide6（Qt6 GUI 框架）
- PyInstaller（打包工具）
- Pillow（图标生成）
- vtracer.exe 0.6.4（已内置于项目根目录）

### 从源码运行

```bash
# 安装依赖
pip install PySide6 pyinstaller pillow

# 直接运行
python app.py
```

### 重新打包 EXE

```bash
pyinstaller VTracerPlus.spec --clean --noconfirm
```

打包产物位于 `dist/VTracerPlus.exe`。

## 📁 项目结构

```
VtracePlus/
├── app.py              # 应用入口
├── main_window.py      # 主窗口与全部交互逻辑
├── converter.py        # vtracer CLI 封装 + 异步转换 Worker + SVG 后处理
├── widgets.py          # 自定义控件（ToggleGroup、ParamSlider 等）
├── styles.py           # 应用 QSS 样式表
├── vtracer.exe         # vtracer 0.6.4 Windows 二进制（内嵌）
├── assets/
│   ├── icon.ico        # 应用图标（多分辨率）
│   ├── icon.png        # 图标 PNG 源文件
│   └── icon_preview.png
├── VTracerPlus.spec    # PyInstaller 打包配置
└── dist/
    └── VTracerPlus.exe # 最终可执行程序
```

## 🎨 参数说明

### 聚类参数

| 参数 | 说明 | 范围 | 默认 |
|------|------|------|------|
| 色彩模式 | 黑白 或 彩色 | bw / color | bw |
| 层级聚类 | 抠图 或 堆叠（仅彩色模式） | cutout / stacked | stacked |
| 去噪强度 | 丢弃小于该像素数的色块，越大越干净 | 0–16 | 4 |
| 色彩精度 | RGB 通道有效位数，越大越精确 | 1–8 | 6 |
| 渐变层级 | 渐变层间色差，越大层数越少 | 1–128 | 16 |

### 曲线拟合参数

| 参数 | 说明 | 范围 | 默认 |
|------|------|------|------|
| 拟合模式 | 像素 / 多边形 / 样条 | pixel/polygon/spline | spline |
| 拐点阈值 | 被视为拐点的最小角度（度），越大越平滑 | 0–180 | 60 |
| 线段长度 | 细分平滑的线段长度上限，越大越粗糙 | 1–64 | 4 |
| 拼接阈值 | 拼接样条的最小角度位移（度） | 0–90 | 45 |

> Path Precision（路径精度）固定为 10，不暴露在 UI 中。

## 📝 致谢

- [visioncortex/vtracer](https://github.com/visioncortex/vtracer) — 核心矢量化引擎
- [PySide6](https://www.qt.io/) — GUI 框架

## 📄 License

本项目基于 visioncortex/vtracer（MIT License）二次开发。
