# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for F76 Price Guide
# Build: pyinstaller F76PriceGuide.spec
# (keep app.ico in the same folder as this spec + F76PriceGuide.py)

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = []
datas += collect_data_files('customtkinter')
datas += collect_data_files('py7zr')

hiddenimports = [
    'customtkinter',
    'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.ImageTk',
    'rapidfuzz', 'rapidfuzz.fuzz', 'rapidfuzz.process',
    'py7zr', 'py7zr.archiveinfo', 'py7zr.compressor', 'py7zr.helpers',
    'py7zr.properties', 'py7zr.exceptions',
    'brotli', 'zstandard', 'pyzstd', 'multivolumefile', 'texttable',
    'requests', 'requests.adapters', 'requests.auth', 'requests.cookies',
    'requests.exceptions', 'requests.models', 'requests.sessions',
    'requests.structures', 'requests.utils',
    'urllib3', 'urllib3.util', 'urllib3.util.retry', 'urllib3.util.ssl_',
    'certifi', 'charset_normalizer', 'idna',
    'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox',
    'http.cookiejar', 'zipfile', 'tempfile', 'threading', 'webbrowser',
    'json', 'pathlib', 'shutil', 'importlib', 'subprocess',
]
hiddenimports += collect_submodules('customtkinter')
hiddenimports += collect_submodules('PIL')
hiddenimports += collect_submodules('py7zr')
hiddenimports += collect_submodules('requests')

a = Analysis(
    ['F76PriceGuide.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PyQt5', 'PyQt6', 'wx', 'gi',
        'IPython', 'jupyter', 'notebook',
        'test', 'tests', 'unittest',
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
    name='F76PriceGuide',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # --noconsole
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',      # --icon=app.ico
    onefile=True,        # --onefile
)
