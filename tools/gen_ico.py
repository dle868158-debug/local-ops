#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Windows EXE 打包资源（开发期工具，不进入 EXE）。

1. build-assets/总控台.ico —— 由 static/assets/console-app-icon.png
   生成 16/24/32/48/64/128/256 全尺寸多分辨率 ICO；
2. build-assets/version_info.txt —— PyInstaller EXE 版本资源
   （任务管理器里显示「总控台」而非 Python），版本号取自根目录 VERSION。

依赖 Pillow（仅构建机需要）。
"""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "static", "assets", "console-app-icon.png")
OUT_DIR = os.path.join(ROOT, "build-assets")
ICO_PATH = os.path.join(OUT_DIR, "总控台.ico")
VERSION_INFO_PATH = os.path.join(OUT_DIR, "version_info.txt")


def read_version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        raw = f.read(128).strip()
    return raw.split("-")[0].split("+")[0]


def write_version_info(version):
    parts = [int(p) if p.isdigit() else 0
             for p in (version.split(".") + ["0", "0", "0", "0"])[:4]]
    content = (
        "# UTF-8\n"
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        "    filevers=(%d, %d, %d, %d),\n"
        "    prodvers=(%d, %d, %d, %d),\n"
        "    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,\n"
        "    date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable('080404b0', [\n"
        "        StringStruct('CompanyName', '本地服务指挥台'),\n"
        "        StringStruct('FileDescription', '总控台 - 本地服务监控与快速启动'),\n"
        "        StringStruct('FileVersion', '%s'),\n"
        "        StringStruct('ProductName', '总控台'),\n"
        "        StringStruct('ProductVersion', '%s'),\n"
        "        StringStruct('OriginalFilename', '总控台.exe')\n"
        "      ])\n"
        "    ]),\n"
        "    VarFileInfo([VarStruct('Translation', [2052, 1200])])\n"
        "  ]\n"
        ")\n"
    ) % (parts[0], parts[1], parts[2], parts[3],
         parts[0], parts[1], parts[2], parts[3], version, version)
    with open(VERSION_INFO_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    if not os.path.isfile(SRC):
        print("缺少源图标: %s" % SRC, file=sys.stderr)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)
    img = Image.open(SRC).convert("RGBA")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    img.save(ICO_PATH, format="ICO", sizes=[(s, s) for s in sizes])
    write_version_info(read_version())
    print("已生成: %s" % ICO_PATH)
    print("已生成: %s" % VERSION_INFO_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
