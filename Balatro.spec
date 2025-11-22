# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata
import os

datas = [('assets', 'assets')]
datas += copy_metadata('imageio')
datas += copy_metadata('moviepy')
datas += copy_metadata('imageio_ffmpeg')
datas += copy_metadata('numpy')


a = Analysis(
    ['game.py'],
    pathex=[os.path.abspath('.')],
    # keep explicit ffmpeg binary entry (source path -> target name inside bundle)
    binaries=[('/Users/adil/Desktop/BalatroPy/venv/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1', 'ffmpeg')],
    datas=datas,
    hiddenimports=['moviepy', 'imageio', 'imageio_ffmpeg', 'numpy'],
    hookspath=[],
    hooksconfig={},
    # add runtime hook to find/make-executable the ffmpeg binary and set IMAGEIO_FFMPEG_EXE
    runtime_hooks=['pyinstaller_hooks/rth_set_ffmpeg.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Balatro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Balatro',
)
app = BUNDLE(
    coll,
    name='Balatro.app',
    icon=None,
    bundle_identifier=None,
)
