"""
vtracer 转换器封装模块
负责调用 vtracer.exe 进行位图到矢量图的转换，并通过 QThread 实现异步执行。
包含 SVG 后处理：清除 color 模式下产生的伪影镂空 path。
"""

import os
import re
import sys
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QThread, Signal, QObject


def get_vtracer_path() -> str:
    """获取 vtracer.exe 的路径，优先使用打包后的路径，其次使用开发环境的路径。"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        base = sys._MEIPASS
        candidate = os.path.join(base, 'vtracer.exe')
        if os.path.exists(candidate):
            return candidate
    # 开发环境：与 app.py 同目录
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, 'vtracer.exe')
    if os.path.exists(candidate):
        return candidate
    # 向上一级
    candidate = os.path.join(os.path.dirname(here), 'vtracer.exe')
    if os.path.exists(candidate):
        return candidate
    return 'vtracer.exe'


@dataclass
class ConversionParams:
    """vtracer 转换参数，分组对应官方 Web 应用的 Clustering 与 Curve Fitting。"""

    # ===== Clustering 参数 =====
    color_mode: str = 'bw'              # 'color' 或 'bw'（默认 bw，与官方建议最小参数一致）
    hierarchical: str = 'stacked'      # 'stacked' 或 'cutout'（仅 color 模式生效）
    filter_speckle: int = 2             # 丢弃小于 X 像素的色块（越大越干净，范围 [0,16]，推荐 0-4）
    color_precision: int = 8            # RGB 通道有效位数（越大越精确，范围 [1,8]，推荐 6-8）
    gradient_step: int = 16            # 渐变层间色差（越大层数越少，范围 [1,128]，推荐 8-32）

    # ===== Curve Fitting 参数 =====
    mode: str = 'spline'               # 'pixel' / 'polygon' / 'spline'
    corner_threshold: int = 30         # 被视为拐点的最小瞬时角度（度，越小保留越多细节）
    segment_length: int = 4            # 细分平滑直到所有线段短于此长度（越小越精细）
    splice_threshold: int = 20         # 拼接样条的最小角度位移（度，越小越精确）
    path_precision: int = 10           # 路径字符串小数位数（越大精度越高）

    # ===== 高级 =====
    preset: Optional[str] = None       # 'bw' / 'poster' / 'photo'，设置后覆盖其它参数

    def to_cli_args(self, input_path: str, output_path: str) -> list:
        """将参数转换为 vtracer 命令行参数列表。"""
        args = [
            '--input', input_path,
            '--output', output_path,
        ]
        if self.preset:
            args.extend(['--preset', self.preset])
            return args

        args.extend([
            '--colormode', self.color_mode,
            '--filter_speckle', str(self.filter_speckle),
            '--color_precision', str(self.color_precision),
            '--gradient_step', str(self.gradient_step),
            '--mode', self.mode,
            '--corner_threshold', str(self.corner_threshold),
            '--segment_length', str(self.segment_length),
            '--splice_threshold', str(self.splice_threshold),
            '--path_precision', str(self.path_precision),
        ])
        # hierarchical 仅在 color 模式下生效
        if self.color_mode == 'color':
            args.extend(['--hierarchical', self.hierarchical])
        return args


# ====== SVG 后处理 ======

def _parse_hex_color(hex_str: str) -> tuple:
    """将 #RRGGBB 转为 (R, G, B) 元组。"""
    h = hex_str.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(c1: tuple, c2: tuple) -> float:
    """计算两个 RGB 颜色之间的欧氏距离。"""
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5


def _estimate_path_area(path_el) -> float:
    """
    粗略估算一个 SVG path 元素的面积（像素²）。
    通过 transform translate 偏移量和 path d 指令中的坐标极值来估算。
    返回 -1 表示无法估算。
    """
    d = path_el.get('d', '')
    if not d:
        return -1.0

    # 解析 transform="translate(x,y)"
    tx, ty = 0.0, 0.0
    transform = path_el.get('transform', '')
    m = re.search(r'translate\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', transform)
    if m:
        tx, ty = float(m.group(1)), float(m.group(2))

    # 从 d 属性提取所有数字作为坐标点
    numbers = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', d)
    if len(numbers) < 2:
        return -1.0
    coords = [float(n) for n in numbers]

    # 取 x/y 的极值估算 bounding box
    xs = [tx + c for i, c in enumerate(coords) if i % 2 == 0]
    ys = [ty + c for i, c in enumerate(coords) if i % 2 == 1]
    if not xs or not ys:
        return -1.0

    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    return max(w * h, 0.0)


def _saturation(rgb: tuple) -> float:
    """计算 RGB 颜色的饱和度（0=灰色，1=完全饱和）。"""
    r, g, b = [c / 255.0 for c in rgb]
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 1e-9:
        return 0.0
    return (mx - mn) / mx


def post_process_svg(svg_path: str):
    """
    对 vtracer 输出的 SVG 进行后处理，清除 color 模式下的伪影镂空 path。

    使用 ElementTree 安全解析和移除，通过自定义序列化避免命名空间前缀变化。
    仅针对明确的伪影（极小面积+背景色附近）进行清理，不做激进的颜色过滤。

    安全保护：若需移除的 path 超过总数的 50%，则跳过。
    """
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        has_ns = '{http://www.w3.org/2000/svg}' in root.tag
        paths = root.findall('.//svg:path', ns) if has_ns else root.findall('.//path')
        total_paths = len(paths)
        if total_paths <= 2:
            return

        # 收集每个 path 的信息
        path_info = []
        for p in paths:
            fill = p.get('fill', '#000000')
            area = _estimate_path_area(p)
            path_info.append((area, fill, p))

        # 按面积排序（大到小），最大的视为背景
        path_info.sort(key=lambda x: x[0], reverse=True)

        bg_area, bg_color, _ = path_info[0]
        bg_rgb = _parse_hex_color(bg_color)
        if bg_area <= 0:
            return

        # 只移除明确的背景附近小碎片（保守策略）
        # 更大的颜色质量改进依赖参数调整（color_precision 等）
        area_threshold = bg_area * 0.003          # 0.3% 背景面积
        color_dist_threshold = 40                   # 颜色距离

        to_remove = []
        for i in range(1, len(path_info)):
            area, fill, el = path_info[i]
            if area < 0:
                continue
            rgb = _parse_hex_color(fill)
            dist = _color_distance(rgb, bg_rgb)
            if dist < color_dist_threshold and area < area_threshold:
                to_remove.append(el)

        # 安全保护
        if len(to_remove) > total_paths // 2:
            return

        if not to_remove:
            return

        for el in to_remove:
            try:
                root.remove(el)
            except ValueError:
                for parent in list(el.iterancestors()):
                    parent.remove(el)
                    break

        # 自定义序列化：保留原始命名空间格式（无前缀）
        _safe_write_svg(tree, svg_path, has_ns, ns)

    except Exception:  # noqa: BLE001
        pass


def _safe_write_svg(tree, output_path: str, has_ns: bool, ns: dict):
    """将 SVG 树写回文件，尽可能保留原始格式（无命名空间前缀变化）。"""
    def _serialize_elem(elem, indent_level: int):
        """递归序列化元素为字符串。"""
        indent = '  ' * indent_level
        parts = []

        # 构建标签名（去掉 Python 的 Clark 表示法中的 namespace 前缀）
        tag = elem.tag
        if tag.startswith('{') and '}' in tag:
            tag = tag.split('}', 1)[1]  # 取 local name

        attrs_str = ''
        for attr_name, val in elem.attrib.items():
            an = attr_name
            if an.startswith('{') and '}' in an:
                an = an.split('}', 1)[1]
            attrs_str += f' {an}="{val}"'

        if len(elem) == 0 and (not elem.text or not elem.text.strip()):
            # 自闭合标签
            parts.append(f'{indent}<{tag}{attrs_str}/>')
        else:
            parts.append(f'{indent}<{tag}{attrs_str}>')
            if elem.text and elem.text.strip():
                parts.append(elem.text.strip())
            for child in elem:
                parts.append(_serialize_elem(child, indent_level + 1))
            if elem.tail and elem.tail.strip():
                parts.append(elem.tail.strip())
            parts.append(f'{indent}</{tag}>')

        return '\n'.join(parts)

    result = [_serialize_elem(tree.getroot(), 0)]
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result))


class ConversionWorker(QThread):
    """在后台线程中执行 vtracer 转换。"""

    progress = Signal(int, str)    # (百分比, 状态文本)
    finished_ok = Signal(str)      # 输出 SVG 路径
    failed = Signal(str)           # 错误信息

    def __init__(self, input_path: str, output_path: str, params: ConversionParams, parent=None):
        super().__init__(parent)
        self._input_path = input_path
        self._output_path = output_path
        self._params = params
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):  # noqa: C901 - 主逻辑
        try:
            if not os.path.exists(self._input_path):
                self.failed.emit(f'输入文件不存在：{self._input_path}')
                return

            vtracer = get_vtracer_path()
            args = [vtracer] + self._params.to_cli_args(self._input_path, self._output_path)

            self.progress.emit(5, '正在启动 vtracer…')

            # 使用 CREATE_NO_WINDOW 避免弹出黑色控制台窗口
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                text=True,
                encoding='utf-8',
                errors='replace',
            )

            # 轮询进程状态，同时推进模拟进度
            import time
            pct = 5
            while True:
                if self._cancelled:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    self.failed.emit('用户已取消转换。')
                    return

                rc = proc.poll()
                if rc is not None:
                    break

                # 进度推进到 90% 封顶，剩余 10% 在完成时补满
                if pct < 90:
                    pct += 1
                    self.progress.emit(pct, f'正在矢量化… {pct}%')
                time.sleep(0.12)

            stdout_data, stderr_data = proc.communicate()

            if proc.returncode != 0:
                msg = (stderr_data or stdout_data or '').strip() or f'vtracer 退出码 {proc.returncode}'
                self.failed.emit(f'转换失败：{msg}')
                return

            if not os.path.exists(self._output_path):
                self.failed.emit('转换未产生输出文件。')
                return

            # SVG 后处理：清除 color 模式下的伪影镂空 path
            post_process_svg(self._output_path)

            self.progress.emit(100, '转换完成！')
            self.finished_ok.emit(self._output_path)
        except FileNotFoundError:
            self.failed.emit('找不到 vtracer.exe，请确保程序文件完整。')
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f'发生异常：{e}')
