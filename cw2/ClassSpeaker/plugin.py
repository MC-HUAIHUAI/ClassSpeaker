# -*- coding: utf-8 -*-
"""教室小喇叭 —— Class Widgets 2 插件入口。

CW2 的插件契约（源码 src/core/plugin/loader.py）：

  * 插件目录里必须有 ``cwplugin.json``，
    必填字段 id / name / version / api_version / entry / author
  * ``entry`` 指向本文件；加载器 ``spec_from_file_location`` 导入后
    取 ``module.Plugin`` 并实例化：``Plugin(plugin_api)``
  * 生命周期：``on_load()`` → 运行期 → ``on_unload()``
  * ``api_version`` 是对插件 API（发行版实为 0.6.0，主分支 0.7.0）的 PEP 440 约束

和 1.x 版本的区别只在「入口 + 设置入口」：
核心（HTTP 服务 / sqlite / 鉴权 / 配置 / 离线 TTS / 教师端网页）原样复用，
UI 从 PyQt5 换成了 PySide6，因此不用写 QML。
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 加载器只在 import 期间把插件目录临时加进 sys.path，之后会恢复；
# 这里常驻加上，保证运行期再 import 子模块也没问题。
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.core.plugin import CW2Plugin  # noqa: E402

META = {
    "id": "com.mchuaihuai.classspeaker",
    "name": "教室小喇叭",
    "author": "MC_HUAIHUAI",
    "version": "2.0.0",
    "api_version": ">=0.6.0",
    "entry": "plugin.py",
}

SETTINGS_SHORTCUT = "settings"


class Plugin(CW2Plugin):
    def __init__(self, plugin_api):
        super().__init__(plugin_api)
        self.core = None
        self.desktop = None
        self._settings = None

    # ---------------- 生命周期 ----------------
    def on_load(self):
        super().on_load()          # 必须：设置 pid / meta / api 上下文

        app = QApplication.instance()
        if app is None:
            self._log("warn", "没有 QApplication，跳过初始化")
            return

        try:
            from classspeaker import SpeakerCore
            from classspeaker.ui import SpeakerDesktop, set_current_core

            self.core = SpeakerCore()
            set_current_core(self.core)      # 让设置窗口拿到核心对象

            # 插件自己建托盘图标（show_tray_icon 默认 true）：
            # CW2 的「快捷方式」是需要用户手动"编辑 -> 添加"才会出现在托盘面板里的，
            # 不直观；自己的图标右键第一项就是「设置…」，最可靠。
            config = self.core.config
            use_tray = bool(config.get("show_tray_icon", True))
            self.desktop = SpeakerDesktop(self.core, app, use_tray=use_tray)
            ok, message = self.desktop.start()
            if ok:
                self._log("info", "服务已启动，教师端地址：{}".format(self.core.address))
            else:
                self._log("error", "服务启动失败：{}".format(message))
        except Exception as exc:
            self._log("error", "初始化失败：{}".format(exc))

        # 设置入口：注册一个 CW2 快捷方式，点开我们自己的设置窗口
        try:
            self.api.ui.register_shortcut(
                SETTINGS_SHORTCUT, "教室小喇叭设置", "icon.png", self.open_settings
            )
            self._log("info", "已注册设置入口（CW2 托盘/快捷方式里）")
        except Exception as exc:
            self._log("warn", "注册设置入口失败：{}".format(exc))

    def on_unload(self):
        try:
            if self.desktop is not None:
                self.desktop.shutdown()
        except Exception as exc:
            self._log("warn", "关闭服务失败：{}".format(exc))
        self.desktop = None
        self.core = None

    # ---------------- 设置窗口 ----------------
    def open_settings(self):
        try:
            from classspeaker.ui import SettingsPanel

            if self._settings is None:
                self._settings = SettingsPanel(self.core)
            self._settings.show()
            self._settings.raise_()
            self._settings.activateWindow()
        except Exception as exc:
            self._log("error", "打开设置失败：{}".format(exc))

    # ---------------- 日志 ----------------
    def _log(self, level, message):
        text = "[教室小喇叭] {}".format(message)
        try:
            from loguru import logger

            getattr(logger, level, logger.info)(text)
        except Exception:
            print(text)
        try:
            from classspeaker import util

            getattr(util.LOG, level if level in ("info", "warn", "error")
                    else "info")(message)
        except Exception:
            pass
