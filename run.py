# -*- coding: utf-8 -*-
"""教室小喇叭 —— 独立版入口（普通版）。

用法：
    pythonw run.py             后台运行，任务栏（托盘）图标常驻
    python  run.py --settings  启动后直接打开设置窗口
    python  run.py --debug     在控制台输出日志（排错用）

说明：
    * 仅依赖 Python 3.8+ 与 PyQt5，无其他第三方库。
    * 设置窗口：托盘图标右键 -> 设置…（首次运行会自动弹出一次）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

MUTEX_NAME = "Local\\ClassSpeaker_SingleInstance"
ERROR_ALREADY_EXISTS = 183


def acquire_single_instance():
    """返回 (是否首个实例, 互斥体句柄)。非 Windows 或失败时一律放行。"""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL,
                                          wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not handle:
            return True, None
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            return False, handle
        return True, handle
    except Exception:
        return True, None


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)

    from PyQt5.QtWidgets import QApplication

    app = QApplication(argv)
    app.setApplicationName("ClassSpeaker")
    app.setQuitOnLastWindowClosed(False)

    from classspeaker import SpeakerCore
    from classspeaker.ui import SpeakerDesktop, style

    app.setWindowIcon(style.build_icon())
    app.setFont(style.app_font())

    first, _handle = acquire_single_instance()
    if not first:
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.information(
            None, style.APP_TITLE,
            "教室小喇叭已在运行。\n请在任务栏右下角的托盘图标上右键 -> 设置…",
        )
        return 0

    core = SpeakerCore()
    desktop = SpeakerDesktop(core, app)
    desktop.start()

    if "--settings" in argv:
        desktop.open_settings()

    try:
        code = app.exec_()
    finally:
        desktop.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
