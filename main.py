# -*- coding: utf-8 -*-
"""教室小喇叭 —— Class Widgets 插件入口（按 CW 真实插件 API 实现）。

CW 的 PluginLoader 会：
    1. 扫描 plugins/ 下每个含 plugin.json 的目录；
    2. 只处理 `config/plugin.json → enabled_plugins` 里列出的插件；
    3. `importlib.import_module("plugins.<目录名>")` —— **按包导入**，
       所以本目录必须有 __init__.py，并由它导出 Plugin / Settings；
    4. `Settings(插件路径)` 构造设置页（可选）；
    5. `Plugin(cw_contexts, method)` 构造插件（可选），稍后调用 execute()，
       之后每个心跳调用 update(cw_contexts)。

安装：把整个 ClassSpeaker 文件夹放进 <CW>\\plugins\\ ，
然后在 CW「设置 → 插件」里启用它。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

WIDGET_CODE = "class-speaker"
WIDGET_NAME = "教室小喇叭"
WIDGET_WIDTH = 220


class Plugin(object):
    def __init__(self, cw_contexts, method):
        # 注意：一定要保存上下文与方法
        self.cw_contexts = cw_contexts or {}
        self.method = method
        self.PATH = self.cw_contexts.get("PLUGIN_PATH") or HERE
        self.core = None
        self.desktop = None
        self._last_widget_text = None
        self._widget_ready = False

        try:
            self.method.register_widget(WIDGET_CODE, WIDGET_NAME, WIDGET_WIDTH)
            self._widget_ready = True
        except Exception as exc:
            self._log("warn", "注册小组件失败（不影响弹窗功能）：{}".format(exc))

    # ---------------- 生命周期 ----------------
    def execute(self):
        """插件加载完成后执行一次。"""
        from PyQt5.QtWidgets import QApplication

        from .classspeaker import SpeakerCore
        from .classspeaker.ui import SpeakerDesktop, set_current_core

        app = QApplication.instance()
        if app is None:
            self._log("warn", "未检测到 QApplication，跳过界面初始化")
            return

        try:
            self.core = SpeakerCore()
            set_current_core(self.core)          # 让 CW 的设置页拿到核心对象
            # 托盘图标跟随配置（默认 true）。插件模式下来自 data/config.json 的
            # "show_tray_icon"；不想要多一个图标就设成 false。
            use_tray = bool(self.core.config.get("show_tray_icon", True))
            self.desktop = SpeakerDesktop(self.core, app, use_tray=use_tray)
            ok, message = self.desktop.start()
            if ok:
                self._log("info", "服务已启动，教师端地址：{}".format(self.core.address))
            else:
                self._log("error", "服务启动失败：{}".format(message))
        except Exception as exc:
            self._log("error", "初始化失败：{}".format(exc))
        self._sync_widget()

    def update(self, cw_contexts):
        """CW 每次心跳都会调用。"""
        self.cw_contexts = cw_contexts or self.cw_contexts
        self._sync_widget()

    # ---------------- 小组件 ----------------
    def _sync_widget(self):
        if not self._widget_ready or self.method is None or self.core is None:
            return
        try:
            running = self.core.server.running
        except Exception:
            running = False
        try:
            pending = self.core.pending_count()
        except Exception:
            pending = 0
        address = self.core.address if running else "服务未启动"
        content = "待确认 {} 条　{}".format(pending, address)
        if content == self._last_widget_text:
            return
        try:
            self.method.change_widget_content(WIDGET_CODE, WIDGET_NAME, content)
            self._last_widget_text = content
        except Exception as exc:
            self._log("warn", "刷新小组件失败：{}".format(exc))

    # ---------------- 日志 ----------------
    def _log(self, level, message):
        try:
            from .classspeaker import util

            getattr(util.LOG, level if level in ("info", "warn", "error")
                    else "info")(message)
        except Exception:
            pass
        try:
            from loguru import logger  # CW 自带

            getattr(logger, level, logger.info)("[教室小喇叭] {}".format(message))
        except Exception:
            print("[教室小喇叭] {}".format(message))


# CW 会在包（plugins.ClassSpeaker）上查找 Settings —— 由 __init__.py 再导出，
# 这里提供一份引用，方便直接 from main import Settings。
from .classspeaker.ui import PluginSettings as Settings  # noqa: E402,F401
from .classspeaker.ui import set_plugin_mode  # noqa: E402,F401

# 告诉设置界面"现在是插件模式"：开机自启之类只对独立版有意义的项要禁用
set_plugin_mode(True)
