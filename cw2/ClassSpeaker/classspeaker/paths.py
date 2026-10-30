# -*- coding: utf-8 -*-
"""路径解析。

同一套代码要同时支持三种运行方式，**都不能靠 sys.frozen 猜**：

  1. 源码运行（python run.py）
  2. Class Widgets 插件（<CW>\\plugins\\ClassSpeaker\\main.py）
  3. PyInstaller 打包后的 exe（onefile / onedir）

坑：Class Widgets 本身就是 PyInstaller 打包的，所以在它进程里
`sys.frozen` 也是 True、`sys._MEIPASS` 也存在 —— 如果据此判断，
插件会把资源目录指向 CW 的临时解压目录、把数据写进 CW 自己的 data 目录。

正确做法：
  * 资源目录永远相对**本文件**推导（web/ 与 assets/ 就在本包旁边）；
  * 数据目录：只有当"本包确实位于 _MEIPASS 里"（说明我们被打包了）
    才用 exe 所在目录，否则用本包的父目录（源码 / 插件目录都成立）。
"""
import os
import sys

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(PACKAGE_DIR, "web")
ASSET_DIR = os.path.join(PACKAGE_DIR, "assets")
DEFAULT_SOUND = os.path.join(ASSET_DIR, "notify.wav")

DATA_DIR_ENV = "CLASSSPEAKER_DATA_DIR"


def is_inside(path, root):
    """path 是否位于 root 之内（大小写不敏感，Windows 友好）。"""
    if not path or not root:
        return False
    path = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(os.path.abspath(root))
    if path == root:
        return True
    return path.startswith(root.rstrip("\\/") + os.sep)


def resolve_app_dir(package_dir, meipass="", executable="", temp_dir=""):
    """返回"程序目录"（放 data/ 的地方）。纯函数，便于测试。

    关键：不能只看 sys.frozen / sys._MEIPASS，因为宿主程序自己也可能被打包过：
      * Class Widgets 是 **onedir** 打包的，它的 sys._MEIPASS 就等于 CW 安装目录，
        而我们的插件正好在 <CW>\\plugins\\ClassSpeaker 下面 —— 一旦据此判断，
        资源会指向 CW 的目录、数据会写进 CW 自己的 data/（已踩过这个坑）。
      * 只有 **onefile** 打包才会把内容解压到 %TEMP%\\_MEIxxxx 这种临时目录。

    所以判定条件收紧为：本包既在 _MEIPASS 里、**又在系统临时目录里** → 我们是被
    onefile 打包的，数据放 exe 旁边（临时目录退出即删）；否则一律用本包的父目录
    （源码运行 = 仓库根目录；插件 = <CW>\\plugins\\ClassSpeaker）。
    """
    parent = os.path.dirname(os.path.abspath(package_dir))
    if not temp_dir:
        import tempfile

        temp_dir = tempfile.gettempdir()
    if (meipass and is_inside(package_dir, meipass)
            and is_inside(package_dir, temp_dir)):
        exe_dir = os.path.dirname(os.path.abspath(executable)) if executable else ""
        return exe_dir or parent
    return parent


APP_DIR = resolve_app_dir(
    PACKAGE_DIR,
    getattr(sys, "_MEIPASS", "") or "",
    getattr(sys, "executable", "") or "",
)
EXE_DIR = APP_DIR   # 兼容旧名字：run.py / exe 所在目录，也是放 data/ 的地方


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
    preferred = os.path.join(APP_DIR, "data")
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
