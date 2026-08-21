# -*- coding: utf-8 -*-
"""总控台 Windows 桌面壳（PySide6 + QtWebEngine）。

仅用于 Windows 单文件 EXE 打包入口（PyInstaller 入口脚本）：
进程内以守护线程运行 server.py 后端，QWebEngineView 加载本机控制台页面，
双击即得原生窗口，无 CMD 黑窗、无需外部浏览器。开发态入口仍是 server.py。

argv 分发（冻结态下由 server.py 的 IS_FROZEN 分支以子进程调用）：
    --tool-anchor <marker> <command>   运行 tools/win_anchor.py 锚点进程
    --pick <dir|script>                运行 tools/win_pick.py 文件/目录选择框
    --restart-helper <pid> <port>      等待旧实例退出并拉起新实例
    --preferred-port <port>            新实例优先复用的端口
默认：启动 GUI 窗口。
"""

import io
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

IS_FROZEN = getattr(sys, "frozen", False)


def resource_path(rel=""):
    """与 server.resource_path 等价的资源根目录（冻结态 sys._MEIPASS）。"""
    if IS_FROZEN and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel) if rel else base


def _ensure_std_streams():
    """无控制台模式（--windowed）下 sys.stdout/stderr 为 None，按需重建。

    --pick 分支的结果要经父进程管道回传，必须保证 stdout 真实可写。
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is not None:
            continue
        fdnum = 1 if name == "stdout" else 2
        try:
            raw = os.fdopen(fdnum, "wb", buffering=0, closefd=False)
        except OSError:
            raw = None
        if raw is None:
            setattr(sys, name, io.StringIO())
        else:
            setattr(sys, name, io.TextIOWrapper(
                raw, encoding="utf-8", errors="replace", line_buffering=True))


def _run_anchor():
    """冻结态锚点进程：等价于 python tools/win_anchor.py <marker> <command>。"""
    import runpy
    sys.argv = [sys.argv[0], sys.argv[2], sys.argv[3]]
    _ensure_std_streams()
    runpy.run_path(resource_path(os.path.join("tools", "win_anchor.py")),
                   run_name="__main__")


def _run_pick():
    """冻结态选择框进程：等价于 python tools/win_pick.py <dir|script>。"""
    import runpy
    what = sys.argv[2] if len(sys.argv) > 2 else "dir"
    sys.argv = [sys.argv[0], what]
    _ensure_std_streams()
    runpy.run_path(resource_path(os.path.join("tools", "win_pick.py")),
                   run_name="__main__")


def _run_restart_helper():
    import server
    old = int(sys.argv[2])
    preferred = int(sys.argv[3])
    sys.exit(server.restart_helper(old, preferred))


def _http_get_json(url, timeout=1.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read(65536).decode("utf-8", "replace"))
    except (OSError, ValueError):
        return None


def _find_console_port(start=9600, tries=10, deadline=20.0):
    """轮询 9600..9609 的 /api/health，命中总控台返回端口，否则 None。"""
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        for port in range(start, start + tries):
            data = _http_get_json("http://127.0.0.1:%d/api/health" % port)
            if data and data.get("status") and "schemaVersion" in data:
                return port
        time.sleep(0.2)
    return None


def _stop_console(port):
    """走 /api/console/stop 优雅停服（窗口关闭时调用）。"""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/console/stop" % port,
            data=b"{}", method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2.0):
            pass
    except OSError:
        pass


def _open_app_flow(port, app_id):
    """桌面快捷方式入口（--open-app <id>）：确保应用就绪后交给系统浏览器。"""
    base = "http://127.0.0.1:%d" % port

    def post(path, data=None):
        try:
            req = urllib.request.Request(
                base + path,
                data=(json.dumps(data).encode("utf-8")
                      if data is not None else b"{}"),
                method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read(65536).decode("utf-8", "replace"))
        except (OSError, ValueError):
            return None

    data = _http_get_json(base + "/api/state", timeout=3)
    app = next((a for a in (data or {}).get("apps", [])
                if a.get("id") == app_id), None)
    if not app:
        return
    kind = app.get("kind") or "service"
    if kind == "link":
        try:
            os.startfile(app["url"])
        except OSError:
            pass
        return
    if kind == "task":
        post("/api/apps/%s/start" % app_id, {})
        return
    # service：未运行则先启动，等监听后打开
    if not app.get("running"):
        post("/api/apps/%s/start" % app_id, {})
    cur = app
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        time.sleep(1.0)
        data = _http_get_json(base + "/api/state", timeout=3)
        cur = next((a for a in (data or {}).get("apps", [])
                    if a.get("id") == app_id), app)
        if cur and cur.get("running"):
            time.sleep(0.5)
            break
    effective_port = None
    if cur and cur.get("ports"):
        effective_port = cur["ports"][0]
    elif app.get("port"):
        effective_port = app["port"]
    if effective_port:
        try:
            os.startfile("http://127.0.0.1:%d/" % int(effective_port))
        except (OSError, TypeError, ValueError):
            pass


def run_gui(preferred_port=None, open_app_id=None):
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QIcon, QKeySequence, QShortcut
    from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu,
                                   QMessageBox, QSystemTrayIcon)
    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineWidgets import QWebEngineView

    import server

    app = QApplication([sys.argv[0]])
    app.setApplicationName("总控台")
    app.setOrganizationName("总控台")
    app.setQuitOnLastWindowClosed(False)  # 关窗缩托盘，由托盘「退出」终结

    # 后端线程：server.main 带实例锁；锁被占则立刻返回 False（viewer 模式）。
    result = {"owned": False}
    threads = []

    def serve(preferred=None):
        try:
            result["owned"] = bool(server.main(
                preferred_port=preferred, open_browser=False,
                log_to_file=True))
        except Exception:
            result["owned"] = False

    def start_server(preferred=None):
        t = threading.Thread(target=serve, kwargs={"preferred": preferred},
                             name="console-server", daemon=True)
        t.start()
        threads.append(t)

    start_server(preferred_port)

    port = _find_console_port()
    if port is None:
        QMessageBox.critical(
            None, "总控台",
            "无法启动总控台（端口 9600-9609 均不可用）。\n"
            "日志见 %s" % server.LOGS_DIR)
        return 1

    state = {"restarting": False, "exit": False, "tray_hint_shown": False}

    class ConsoleWindow(QMainWindow):
        def __init__(self, view, server_port):
            super().__init__()
            self._server_port = server_port
            self._closing = False
            self._tray = None
            self.setWindowTitle("总控台")
            self.resize(1280, 860)
            self.setMinimumSize(1024, 700)
            icon_path = resource_path(
                os.path.join("static", "assets", "console-app-icon.png"))
            if os.path.isfile(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            self.setCentralWidget(view)

        def closeEvent(self, event):
            self._closing = True
            if not result["owned"]:
                # viewer 实例：直接退出本进程
                QApplication.quit()
                event.accept()
                return
            if state["exit"] or state["restarting"]:
                event.accept()
                return
            # 缩到托盘继续守护服务（守护/自启在后台线程照常运行）
            self.hide()
            if not state["tray_hint_shown"]:
                state["tray_hint_shown"] = True
                if self._tray:
                    self._tray.showMessage(
                        "总控台",
                        "已最小化到托盘，服务守护仍在后台运行。\n"
                        "托盘图标右键可退出。")
            event.ignore()

    class ConsolePage(QWebEnginePage):
        """页面里的 window.open（服务卡片「打开」等）转交系统默认浏览器。

        QWebEngineView 默认不展示弹窗，桌面 EXE 里点服务卡片端口会静默失败；
        拦截 http/https 弹窗交给 os.startfile，与网址卡片行为一致。
        """

        def createWindow(self, _wintype):
            url = self.requestedUrl()
            if url.isValid() and url.scheme() in ("http", "https"):
                try:
                    os.startfile(url.toString())
                except OSError:
                    pass
            return None

    view = QWebEngineView()
    view.setPage(ConsolePage(view))
    window = ConsoleWindow(view, port)

    # 系统托盘：双击图标显示窗口；「退出」才真正结束进程与服务
    try:
        tray = QSystemTrayIcon(QIcon(resource_path(
            os.path.join("static", "assets", "console-app-icon.png"))), app)
        tray.setToolTip("总控台")
        menu = QMenu()
        act_show = menu.addAction("打开总控台")
        act_show.triggered.connect(lambda: (
            window.showNormal(), window.raise_(), window.activateWindow()))
        menu.addSeparator()
        act_exit = menu.addAction("退出")

        def tray_exit():
            state["exit"] = True
            if result["owned"]:
                _stop_console(port)
            window.close()
            QApplication.quit()

        act_exit.triggered.connect(tray_exit)
        tray.setContextMenu(menu)

        def on_tray_activate(reason):
            if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                          QSystemTrayIcon.ActivationReason.DoubleClick):
                window.showNormal()
                window.raise_()
                window.activateWindow()

        tray.activated.connect(on_tray_activate)
        tray.show()
        window._tray = tray
    except Exception:
        window._tray = None

    QShortcut(QKeySequence("F5"), window, activated=view.reload)
    QShortcut(QKeySequence("F11"), window,
              activated=lambda: window.showFullScreen()
              if not window.isFullScreen() else window.showNormal())

    timer = QTimer(window)
    timer.setInterval(500)

    def watchdog():
        # 页面里点了「停止总控台」→ 后端线程退出 → GUI 退出。
        # 「重启总控台」→ 同进程重启服务线程并刷新页面：不 spawn 第二个
        # onefile 实例，彻底避开嵌套实例解压目录被清理的坑。
        if (result["owned"] and not threads[-1].is_alive()
                and not window._closing):
            pending = getattr(server, "PENDING_FROZEN_RESTART", {}).get("port")
            if pending:
                state["restarting"] = True
                server.PENDING_FROZEN_RESTART["port"] = None
                start_server(int(pending))
                # Qt 对象只能在主线程操作：用 QTimer 在主线程探测就绪后刷新，
                # 绝不能在后台线程调 view.load()（会硬崩溃）。
                reload_timer = QTimer(window)
                reload_timer.setInterval(400)
                window._reload_timer = reload_timer

                def probe_reload():
                    for probe_port in range(9600, 9610):
                        if _http_get_json(
                                "http://127.0.0.1:%d/api/health" % probe_port,
                                timeout=0.4):
                            reload_timer.stop()
                            view.load(QUrl(
                                "http://127.0.0.1:%d/" % probe_port))
                            return
                reload_timer.timeout.connect(probe_reload)
                reload_timer.start()
            else:
                QApplication.quit()

    timer.timeout.connect(watchdog)
    timer.start()

    view.load(QUrl("http://127.0.0.1:%d/" % port))
    window.show()
    if open_app_id:
        threading.Thread(target=_open_app_flow, args=(port, open_app_id),
                         name="console-open-app", daemon=True).start()
    return app.exec()


def main():
    if "--tool-anchor" in sys.argv:
        _run_anchor()
        return 0
    if "--pick" in sys.argv:
        _run_pick()
        return 0
    if "--restart-helper" in sys.argv:
        _run_restart_helper()
        return 0
    preferred = None
    if "--preferred-port" in sys.argv:
        try:
            preferred = int(sys.argv[sys.argv.index("--preferred-port") + 1])
        except (ValueError, IndexError):
            preferred = None
    open_app = None
    if "--open-app" in sys.argv:
        try:
            open_app = sys.argv[sys.argv.index("--open-app") + 1]
        except IndexError:
            open_app = None
    return run_gui(preferred_port=preferred, open_app_id=open_app)


if __name__ == "__main__":
    sys.exit(main())
