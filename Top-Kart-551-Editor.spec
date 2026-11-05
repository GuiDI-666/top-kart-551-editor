# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：主编辑器（需要 Top-Kart.dll 做解析与回读校验）。

用法：pyinstaller Top-Kart-551-Editor.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs

ROOT = Path(SPECPATH).resolve()

# 从当前 Python 环境定位 unicorn 的动态库，避免写死 site-packages 绝对路径。
unicorn_binaries = collect_dynamic_libs("unicorn")

a = Analysis(
    [str(ROOT / "551密文编辑器_tk.py")],
    pathex=[str(ROOT)],
    binaries=unicorn_binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Top-Kart-551-Editor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
