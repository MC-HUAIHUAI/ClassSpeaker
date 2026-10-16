# -*- coding: utf-8 -*-
"""开机自启动（Windows：写入当前用户的注册表 Run 项，无需管理员权限）。

* 独立版 / exe 版：注册 `"<pythonw.exe>" "<run.py>"` 或 `"<ClassSpeaker.exe>"`
* 关闭时删除该值
* 所有函数的 name 参数默认取 VALUE_NAME，且是**运行时**读取，
  所以测试可以临时替换成别的项名，绝不碰正式那条。
"""
import os
import sys

from . import paths, util

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ClassSpeaker"


def supported():
    return sys.platform.startswith("win")


def _winreg():
    import winreg  # 仅 Windows 有

    return winreg


def _resolve_name(name):
    return name or VALUE_NAME


def python_launcher():
    """脚本运行时优先用 pythonw.exe（无黑色控制台窗口）。"""
    python = sys.executable or ""
    if not python:
        return "pythonw.exe"
    if python.lower().endswith("python.exe"):
        candidate = python[: -len("python.exe")] + "pythonw.exe"
        if os.path.isfile(candidate):
            return candidate
    return python


def launch_command():
    """开机时实际执行的命令行。"""
    if getattr(sys, "frozen", False):
        return '"{}"'.format(os.path.abspath(sys.executable))
    script = os.path.join(paths.EXE_DIR, "run.py")
    return '"{}" "{}"'.format(
        os.path.abspath(python_launcher()), os.path.abspath(script)
    )


def current_value(name=None):
    """返回注册表里当前记录的命令，没有则返回空串。"""
    if not supported():
        return ""
    name = _resolve_name(name)
    try:
        winreg = _winreg()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, name)
            return value or ""
    except Exception:
        return ""


def is_enabled(name=None):
    return bool(current_value(name))


def is_current(name=None):
    """自启项存在，且指向的就是当前这份程序。"""
    return current_value(name).strip() == launch_command().strip()


def enable(name=None):
    if not supported():
        return False, "当前系统不支持注册表自启（仅 Windows）"
    name = _resolve_name(name)
    if not getattr(sys, "frozen", False) and \
            not os.path.isfile(os.path.join(paths.EXE_DIR, "run.py")):
        return False, "找不到 run.py，无法设置自启"
    command = launch_command()
    try:
        winreg = _winreg()
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
    except Exception as exc:
        util.LOG.warn("写入开机自启失败：{}".format(exc))
        return False, "写入注册表失败：{}".format(exc)
    util.LOG.info("已开启开机自启：{}".format(command))
    return True, "已开启开机自启"


def disable(name=None):
    if not supported():
        return False, "当前系统不支持注册表自启（仅 Windows）"
    name = _resolve_name(name)
    try:
        winreg = _winreg()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        return True, "开机自启本来就是关闭的"
    except Exception as exc:
        util.LOG.warn("删除开机自启失败：{}".format(exc))
        return False, "删除注册表项失败：{}".format(exc)
    util.LOG.info("已关闭开机自启")
    return True, "已关闭开机自启"


def apply(enabled, name=None):
    """按需要开启/关闭；已处于目标状态时不重复写注册表。"""
    if enabled:
        if is_current(name):
            return True, "开机自启已开启"
        return enable(name)
    if not is_enabled(name):
        return True, "开机自启已关闭"
    return disable(name)
