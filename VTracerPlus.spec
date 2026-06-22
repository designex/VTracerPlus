# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
将 VTracer Plus 打包为单文件 Windows EXE，内嵌 vtracer.exe。
"""

import os

block_cipher = None
here = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['app.py'],
    pathex=[here],
    binaries=[],
    datas=[
        # 将 vtracer.exe 打包到 EXE 内部
        (os.path.join(here, 'vtracer.exe'), '.'),
        # 应用图标（运行时用于窗口图标显示）
        (os.path.join(here, 'assets', 'icon.ico'), 'assets'),
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大模块以减小体积
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PySide6.Qt3D',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtMultimedia',
        'PySide6.QtNetwork',
        'PySide6.QtOpenGL',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtQuick3D',
        'PySide6.QtQuickWidgets',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets',
        'PySide6.QtXml',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VTracerPlus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(here, 'assets', 'icon.ico'),
)
