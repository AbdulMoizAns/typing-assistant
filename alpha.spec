# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ALPHA Typing Assistant.

Build a standalone executable with:

    pyinstaller alpha.spec

The resulting ``dist/ALPHA_Typing_Assistant.exe`` runs without a Python
installation and keeps every data file next to the executable.
"""
import os

block_cipher = None

DATA_FILES = [
    ("suggestions.json", "."),
    ("errors.json", "."),
    ("frequency_words.json", "."),
    ("dictionary.json", "."),
    ("sequences.json", "."),
    ("app_icon.ico", "."),
    ("app_icon_32.png", "."),
]

a = Analysis(
    ["alpha_assistant.py"],
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=DATA_FILES,
    hiddenimports=["pynput._util.win32", "pynput._util.win32_vks"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "test", "unittest"],
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
    name="ALPHA_Typing_Assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app_icon.ico",
)
