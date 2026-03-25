# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for SimTelemetry Pro

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all hidden imports needed
hidden_imports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'pyqtgraph',
    'pyqtgraph.graphicsItems',
    'anthropic',
    'httpx',
    'pandas',
    'numpy',
    'psutil',
    'ctypes',
    'ctypes.wintypes',
    'csv',
    'json',
    'threading',
    'pathlib',
    'dataclasses',
]

hidden_imports += collect_submodules('pyqtgraph')
hidden_imports += collect_submodules('anthropic')

# Collect pyqtgraph data files (colormaps, icons, etc.)
datas = []
datas += collect_data_files('pyqtgraph')
# Bundle the assets folder (steering wheel image, icon, etc.)
datas += [('assets', 'assets')]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'IPython',
        'jupyter', 'notebook', 'PIL', 'cv2',
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
    [],
    exclude_binaries=True,
    name='SimTelemetryPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no black console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if Path('assets/icon.ico').exists() else None,
    version='version_info.txt' if Path('version_info.txt').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SimTelemetryPro',
)
