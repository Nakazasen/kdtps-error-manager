# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for KDTPS Error Manager
Build command: pyinstaller kdtps.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Project root
project_root = Path('.').resolve()
src_path = project_root / 'src'

a = Analysis(
    ['src/main.py'],
    pathex=[str(src_path)],
    binaries=[],
    datas=[
        ('data/ai_settings.json', 'data'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'win32com',
        'win32com.client',
        'pythoncom',
        'google.genai',
        'deep_translator',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
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
    a.zipfiles,
    a.datas,
    [],
    name='KDTPS_Error_Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
