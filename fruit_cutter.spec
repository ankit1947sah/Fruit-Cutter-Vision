# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect all dynamic libraries and data assets for critical binary packages
mediapipe_datas = collect_data_files('mediapipe')
mediapipe_binaries = collect_dynamic_libs('mediapipe')

cv2_datas = collect_data_files('cv2')
cv2_binaries = collect_dynamic_libs('cv2')

pygame_datas = collect_data_files('pygame')

datas = [] + mediapipe_datas + cv2_datas + pygame_datas
binaries = [] + mediapipe_binaries + cv2_binaries

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'numpy',
        'pygame',
        'pygame.mixer',
        'pygame.sndarray',
        'cv2',
        'mediapipe',
        'psutil'
    ],
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
    [],
    exclude_binaries=True,
    name='FruitCutterVision',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to True if terminal logging output is desired at runtime
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements=file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FruitCutterVision',
)
