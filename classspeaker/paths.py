# -*- coding: utf-8 -*-
"""路径解析。

同一套代码要同时支持：
  1. 独立运行（python run.py）
  2. Class Widgets 插件（plugins/ClassSpeaker/main.py）
  3. PyInstaller 打包后的 exe（onefile / onedir）

关键区分：
  * EXE_DIR / APP_DIR —— 可写位置，exe 或 run.py 所在的目录，data/ 放这里
  * RESOURCE_DIR      —— 只读资源位置（web/ 与 assets/），onefile 打包后是 _MEIPASS
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCE_ROOT = os.path.dirname(_HERE)


def _is_frozen():
    return bool(getattr(sys, "frozen", False))


def _exe_dir():
    try:
        return os.path.dirname(os.path.abspath(sys.executable))
    except Exception:
        return _SOURCE_ROOT


if _is_frozen():
    # 数据写在 exe 旁边（不可写时再退到用户目录）
    EXE_DIR = _exe_dir()
    _meipass = getattr(sys, "_MEIPASS", "") or ""
    if _meipass and os.path.isdir(os.path.join(_meipass, "classspeaker")):
        RESOURCE_DIR = _meipass
    elif os.path.isdir(os.path.join(EXE_DIR, "classspeaker")):
        RESOURCE_DIR = EXE_DIR
    else:
        RESOURCE_DIR = _meipass or EXE_DIR
else:
    EXE_DIR = _SOURCE_ROOT
    RESOURCE_DIR = _SOURCE_ROOT

APP_DIR = EXE_DIR          # 兼容旧名字
PACKAGE_DIR = os.path.join(RESOURCE_DIR, "classspeaker")
WEB_DIR = os.path.join(PACKAGE_DIR, "web")
ASSET_DIR = os.path.join(PACKAGE_DIR, "assets")
DEFAULT_SOUND = os.path.join(ASSET_DIR, "notify.wav")

DATA_DIR_ENV = "CLASSSPEAKER_DATA_DIR"


def _writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_probe")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def _resolve_data_dir():
    """优先顺序：环境变量 > 程序目录下的 data > %LOCALAPPDATA%\\ClassSpeaker。"""
    override = (os.environ.get(DATA_DIR_ENV) or "").strip()
    if override:
        override = os.path.abspath(os.path.expanduser(override))
        try:
            os.makedirs(override, exist_ok=True)
        except Exception:
            pass
        return override
    preferred = os.path.join(EXE_DIR, "data")
    if _writable(preferred):
        return preferred
    fallback = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "ClassSpeaker"
    )
    os.makedirs(fallback, exist_ok=True)
    return fallback


DATA_DIR = _resolve_data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
DB_PATH = os.path.join(DATA_DIR, "speaker.db")
LOG_PATH = os.path.join(DATA_DIR, "server.log")


def ensure_dirs():
    for path in (DATA_DIR,):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
