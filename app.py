"""
VTracer Plus 应用入口
基于 visioncortex/vtracer 的 Windows 桌面位图转矢量图工具。
"""

import os
import sys

# 确保打包后能找到同目录的模块与 vtracer.exe
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from main_window import MainWindow
from styles import APP_QSS


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName('VTracer Plus')
    app.setOrganizationName('VTracerPlus')
    app.setStyleSheet(APP_QSS)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
