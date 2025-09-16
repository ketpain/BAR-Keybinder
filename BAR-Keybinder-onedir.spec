# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all PyQt6 plugins and modules that may be needed
hiddenimports = []
hiddenimports += collect_submodules('PyQt6')
hiddenimports += collect_submodules('PyQt6.QtWidgets')
hiddenimports += collect_submodules('PyQt6.QtGui')
hiddenimports += collect_submodules('PyQt6.QtCore')
hiddenimports += collect_submodules('qdarktheme')

project_dir = os.getcwd()
assets = []
assets += collect_data_files('qdarktheme')

# Data files to include: put defaults under a dedicated folder
data_files = [
    ('default keys.txt', 'defaults'),
    (os.path.join('assets', 'icon.ico'), 'assets'),
    (os.path.join('assets', 'icon.png'), 'assets'),
    ('icon.ico', '.'),
    ('icon.png', '.'),
]

for src_rel, dest_dir in data_files:
    p = os.path.join(project_dir, src_rel)
    if os.path.exists(p):
        assets.append((p, dest_dir))


a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=assets,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='BAR-Keybinder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    console=False,
    icon=os.path.join(project_dir, 'assets', 'icon.ico') if os.path.exists(os.path.join(project_dir, 'assets', 'icon.ico')) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BAR-Keybinder'
)
