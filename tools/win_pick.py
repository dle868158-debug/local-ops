#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Windows Vista+ 文件/目录选择框（IFileOpenDialog）。

由 server.py 的 _pick_path_windows 拉起独立进程，避免在 HTTP 工作线程
里做 COM STA。目录模式使用 FOS_PICKFOLDERS，交互与资源管理器一致，
可以双击进入子目录；旧版 FolderBrowserDialog 做不到这一点。

stdout：选中路径，或用户取消时输出 __CANCELED__。
"""

import ctypes
import sys
from ctypes import wintypes

ole32 = ctypes.OleDLL("ole32")
user32 = ctypes.WinDLL("user32")

COINIT_APARTMENTTHREADED = 0x2
CLSCTX_INPROC_SERVER = 0x1
S_OK = 0
HRESULT_CANCELLED = 0x800704C7
FOS_PICKFOLDERS = 0x20
FOS_FORCEFILESYSTEM = 0x40
FOS_PATHMUSTEXIST = 0x800
FOS_FILEMUSTEXIST = 0x1000
FOS_DONTADDTORECENT = 0x02000000
SIGDN_FILESYSPATH = 0x80058000
CLSID_FILE_OPEN_DIALOG = "{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}"
IID_IFILE_OPEN_DIALOG = "{D57C7288-D4AD-4768-BE02-9D969532D960}"

IDX_RELEASE = 2
IDX_SHOW = 3
IDX_SET_FILE_TYPES = 4
IDX_SET_OPTIONS = 9
IDX_SET_TITLE = 17
IDX_GET_RESULT = 20
IDX_GET_DISPLAY_NAME = 5


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

    def __init__(self, value):
        super().__init__()
        ole32.IIDFromString(value, ctypes.byref(self))


class COMDLG_FILTERSPEC(ctypes.Structure):
    _fields_ = [
        ("pszName", wintypes.LPCWSTR),
        ("pszSpec", wintypes.LPCWSTR),
    ]


ole32.IIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(GUID)]
ole32.IIDFromString.restype = ctypes.HRESULT
ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
ole32.CoInitializeEx.restype = ctypes.HRESULT
ole32.CoUninitialize.argtypes = []
ole32.CoCreateInstance.argtypes = [
    ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_uint32,
    ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
ole32.CoCreateInstance.restype = ctypes.HRESULT
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
user32.AllowSetForegroundWindow.restype = wintypes.BOOL


def _as_uint(hr):
    return hr & 0xFFFFFFFF


def _vtable(punk):
    return ctypes.cast(
        ctypes.cast(punk, ctypes.POINTER(ctypes.c_void_p)).contents,
        ctypes.POINTER(ctypes.c_void_p))


def _fn(punk, index, restype, *argtypes):
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(_vtable(punk)[index])


def _release(punk):
    if not punk:
        return
    _fn(punk, IDX_RELEASE, ctypes.c_ulong)(punk)


def _create_dialog():
    """CoCreate IFileOpenDialog。失败返回 None。调用方必须 _release。"""
    clsid = GUID(CLSID_FILE_OPEN_DIALOG)
    iid = GUID(IID_IFILE_OPEN_DIALOG)
    punk = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        ctypes.byref(clsid), None, CLSCTX_INPROC_SERVER,
        ctypes.byref(iid), ctypes.byref(punk))
    if _as_uint(hr) != S_OK or not punk:
        return None
    return punk


def _shell_item_path(item):
    ptr = ctypes.c_void_p()
    hr = _fn(item, IDX_GET_DISPLAY_NAME, ctypes.c_long,
             ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p))(
                 item, SIGDN_FILESYSPATH, ctypes.byref(ptr))
    if _as_uint(hr) != S_OK or not ptr:
        return None
    try:
        return ctypes.wstring_at(ptr)
    finally:
        ole32.CoTaskMemFree(ptr)


def pick(what):
    """打开系统选择框。返回路径字符串、'__CANCELED__' 或 None（失败）。"""
    mode = "dir" if what == "dir" else "script"
    hr_init = _as_uint(ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED))
    if hr_init not in (S_OK, 0x00000001):  # S_FALSE = already initialized
        return None
    dialog = _create_dialog()
    if dialog is None:
        ole32.CoUninitialize()
        return None
    try:
        options = FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST | FOS_DONTADDTORECENT
        title = "选择工作目录"
        if mode == "dir":
            options |= FOS_PICKFOLDERS
        else:
            options |= FOS_FILEMUSTEXIST
            title = "选择批处理脚本"
            filters = (COMDLG_FILTERSPEC * 2)(
                COMDLG_FILTERSPEC("脚本文件", "*.py;*.ps1;*.bat;*.cmd;*.sh"),
                COMDLG_FILTERSPEC("所有文件", "*.*"),
            )
            _fn(dialog, IDX_SET_FILE_TYPES, ctypes.c_long,
                ctypes.c_uint, ctypes.c_void_p)(
                    dialog, 2, ctypes.cast(filters, ctypes.c_void_p))
        _fn(dialog, IDX_SET_OPTIONS, ctypes.c_long, ctypes.c_uint)(
            dialog, options)
        _fn(dialog, IDX_SET_TITLE, ctypes.c_long, wintypes.LPCWSTR)(
            dialog, title)
        try:
            user32.AllowSetForegroundWindow(0xFFFFFFFF)
        except OSError:
            pass
        owner = user32.GetForegroundWindow()
        hr = _fn(dialog, IDX_SHOW, ctypes.c_long, wintypes.HWND)(
            dialog, owner)
        code = _as_uint(hr)
        if code == HRESULT_CANCELLED:
            return "__CANCELED__"
        if code != S_OK:
            return None
        item = ctypes.c_void_p()
        hr = _fn(dialog, IDX_GET_RESULT, ctypes.c_long,
                 ctypes.POINTER(ctypes.c_void_p))(dialog, ctypes.byref(item))
        if _as_uint(hr) != S_OK or not item:
            return None
        try:
            return _shell_item_path(item)
        finally:
            _release(item)
    finally:
        _release(dialog)
        ole32.CoUninitialize()


def self_test():
    """不弹窗：只验证 COM 对象能创建。成功返回 0。"""
    hr_init = _as_uint(ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED))
    if hr_init not in (S_OK, 0x00000001):
        return 1
    dialog = _create_dialog()
    if dialog is None:
        ole32.CoUninitialize()
        return 1
    _release(dialog)
    ole32.CoUninitialize()
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--self-test"]:
        return self_test()
    what = args[0] if args else "dir"
    if what not in ("dir", "script"):
        sys.stderr.write("usage: win_pick.py dir|script|--self-test\n")
        return 2
    result = pick(what)
    if result is None:
        return 1
    sys.stdout.write(result + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
