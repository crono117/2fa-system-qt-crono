# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for 2FA Merchant Verification System (PySide2 / Qt)

Build on Windows:  build_exe.bat
Build on Linux:    ./build_exe.sh
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

SPEC_DIR = Path(SPECPATH).resolve()

# Collect all files for key packages
requests_datas,      requests_binaries,      requests_hiddenimports      = collect_all('requests')
cryptography_datas,  cryptography_binaries,  cryptography_hiddenimports  = collect_all('cryptography')
loguru_datas,        loguru_binaries,        loguru_hiddenimports        = collect_all('loguru')
urllib3_datas,       urllib3_binaries,       urllib3_hiddenimports       = collect_all('urllib3')
certifi_datas,       certifi_binaries,       certifi_hiddenimports       = collect_all('certifi')

all_datas = (
    requests_datas + cryptography_datas + loguru_datas +
    urllib3_datas  + certifi_datas
)
all_binaries = (
    requests_binaries + cryptography_binaries + loguru_binaries +
    urllib3_binaries  + certifi_binaries
)
all_hiddenimports = (
    requests_hiddenimports + cryptography_hiddenimports + loguru_hiddenimports +
    urllib3_hiddenimports  + certifi_hiddenimports
)

hidden_imports = all_hiddenimports + [
    # PySide2 / Qt modules used by the app
    'PySide2.QtWidgets',
    'PySide2.QtCore',
    'PySide2.QtGui',
    'PySide2.QtNetwork',
    'PySide2.QtWebSockets',

    # HTTP
    'requests',
    'urllib3',
    'urllib3.util.retry',
    'certifi',

    # Security / keyring
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'keyring',
    'keyring.backends',
    'keyring.backends.fail',
    'keyring.backends.null',
    # Windows keyring backend (active on target machine)
    'keyring.backends.Windows',

    # Logging
    'loguru',

    # Standard library modules PyInstaller sometimes misses
    'configparser',
    'json',
    'threading',
    'queue',
    'uuid',
    'hashlib',
    'base64',
    'ssl',
    'socket',
    'enum',
    'dataclasses',
    'pathlib',
]

a = Analysis(
    ['run.py'],
    pathex=[str(SPEC_DIR), str(SPEC_DIR / 'src')],
    binaries=all_binaries,
    datas=[
        # Ship config.ini so the server URL is editable without rebuilding
        ('config.ini', '.'),
    ] + all_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Test tooling
        'pytest', '_pytest', 'pytest_qt', 'coverage',
        # Dev tools
        'IPython', 'jupyter', 'black', 'flake8', 'mypy',
        # Heavy packages not used by this app
        'matplotlib', 'numpy', 'pandas', 'scipy',
        # Tkinter / CustomTkinter (old frontend — not needed here)
        'tkinter', 'customtkinter',
        # Old WebSocket library replaced by QWebSocket
        'websocket',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='2FA_System',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # UPX compression — reduces file size if UPX is installed
    upx_exclude=[
        # Never compress Qt DLLs — UPX breaks them
        'Qt5Core.dll', 'Qt5Gui.dll', 'Qt5Widgets.dll',
        'Qt5Network.dll', 'Qt5WebSockets.dll',
        'shiboken2.cpython*.pyd',
        'PySide2.cpython*.pyd',
    ],
    runtime_tmpdir=None,
    console=False,      # No terminal window — logs go to ~/.merchant_verification_qt/logs/
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # Add path to a .ico file here if you have one
)
