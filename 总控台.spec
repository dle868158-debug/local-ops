# -*- mode: python ; coding: utf-8 -*-
"""总控台 Windows 单文件 EXE 打包配置（PySide6 壳 + 进程内后端）。

用法:
    python -m PyInstaller 总控台.spec --noconfirm --clean

说明:
- 入口 console_gui.py：QWebEngineView 原生窗口 + 线程内运行 server.py；
  console=False 即无 CMD 黑窗（--windowed）。
- datas：static/ 前端全部资源（html/js/css/主题/字体/图标）、VERSION、
  tools/win_anchor.py、win_pick.py。冻结态下由 server.py 的 IS_FROZEN
  分支通过子进程 argv（--tool-anchor / --pick）分发调用，路径经
  resource_path()（sys._MEIPASS）解析。
- hiddenimports：本项目除 PySide6 外无隐藏依赖，留空是正确做法。
  若打包真正的 PyQt 项目，常见补丁形如：
      hiddenimports=["PyQt5.sip", "PyQt5.QtWidgets", "PyQt5.QtGui"]
- binaries：本项目纯标准库 + 系统 DLL，留空。若启动报
  "DLL load failed"，把缺失 DLL 以 ("绝对路径\\xxx.dll", ".") 加入。
- upx=False：QtWebEngine 的 DLL 不建议 UPX（易坏且加重杀软误报）。
  如需压缩：下载 upx-*-win64.zip，加参数 --upx-dir=<解压目录>。
- 首次启动慢属正常：onefile 每次运行先解压到 %TEMP%\\_MEIxxxx。
"""

import os

project_root = SPECPATH  # spec 文件所在目录

datas = [
    (os.path.join(project_root, "static"), "static"),
    (os.path.join(project_root, "VERSION"), "."),
    (os.path.join(project_root, "tools", "win_anchor.py"), "tools"),
    (os.path.join(project_root, "tools", "win_pick.py"), "tools"),
]

a = Analysis(
    [os.path.join(project_root, "console_gui.py")],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc"],
    noarchive=False,
)


def _is_foreign_binary(src):
    """剔除绝不应打包的 DLL。

    - 系统 UCRT / API Set（api-ms-win-*、ext-ms-*、ucrtbase.dll）：
      Windows 自带，打包旧副本会被 Qt6Core 优先加载，报
      "找不到指定的程序"（导出缺失）；
    - Anaconda/Miniconda 目录出来的任何 DLL：机器 PATH 上有 conda 时，
      PyInstaller 依赖扫描会捡到它的旧版 ucrtbase/openssl/icu 打进包里。
    """
    src_lower = (src or "").lower()
    if "anaconda" in src_lower or "miniconda" in src_lower:
        return True
    name = os.path.basename(src or "").lower()
    return (name.startswith("api-ms-win-") or name.startswith("ext-ms-")
            or name == "ucrtbase.dll")


a.binaries = [b for b in a.binaries if not _is_foreign_binary(b[1])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="总控台",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(project_root, "build-assets", "总控台.ico"),
    version=os.path.join(project_root, "build-assets", "version_info.txt"),
)
