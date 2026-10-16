# -*- coding: utf-8 -*-
"""教室小喇叭 —— Class Widgets 插件入口。

安装：把整个 ClassSpeaker 文件夹放进 Class Widgets 的 plugins 目录：
    ClassWidgets-Windows-x64/plugins/ClassSpeaker/
        plugin.json
        main.py        <- 本文件
        classspeaker/  <- 核心代码 + 网页 + 声音
        run.py         <- 独立版入口（可选，插件模式下用不到）

插件会：
    1. 在 Class Widgets 进程内启动同一个局域网服务与弹窗程序；
    2. 注册一个小组件，显示"待确认条数 + 教师端地址"，方便老师找到入口；
    3. 自带托盘图标，右键 -> 设置…（与独立版完全一致）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

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
        except Exception as exc:  # 老版本没有该接口时不影响主功能
            self._log("warn", "注册小组件失败：{}".format(exc))

    # ---------------- 插件生命周期 ----------------
    def execute(self):
        """插件加载时执行一次。"""
        from PyQt5.QtWidgets import QApplication

        from classspeaker import SpeakerCore
        from classspeaker.ui import SpeakerDesktop

        app = QApplication.instance()
        if app is None:
            self._log("warn", "未检测到 QApplication，跳过界面初始化")
            return

        try:
            self.core = SpeakerCore()
            self.desktop = SpeakerDesktop(self.core, app)
            ok, message = self.desktop.start()
            if ok:
                self._log("info", "服务已启动，教师端地址：{}".format(self.core.address))
            else:
                self._log("error", "服务启动失败：{}".format(message))
        except Exception as exc:
            self._log("error", "初始化失败：{}".format(exc))
        self._sync_widget()

    def update(self, cw_contexts):
        """Class Widgets 每次心跳都会调用。"""
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
            from classspeaker import util

            getattr(util.LOG, level if level in ("info", "warn", "error")
                    else "info")(message)
        except Exception:
            pass
        try:
            from utils import logger  # Class Widgets 自带日志

            getattr(logger, level, logger.info)("[教室小喇叭] {}".format(message))
        except Exception:
            print("[教室小喇叭] {}".format(message))
