# -*- coding: utf-8 -*-
"""Class Widgets 2 插件测试：不需要真的 CW2。

    set QT_QPA_PLATFORM=offscreen
    python tools/cw2_test.py

做两件事：
  1. 用假的 `src.core.plugin`（按 CW2 源码的契约）加载 cw2/ClassSpeaker/plugin.py，
     走一遍 on_load -> 注册设置入口 -> on_unload；
  2. 验证 PySide6 版的弹窗 / 设置面板能正常创建、行为与 1.x 版一致。
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

os.environ["CLASSSPEAKER_DATA_DIR"] = tempfile.mkdtemp(prefix="classspeaker_cw2_data_")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, "cw2", "ClassSpeaker")
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  [PASS] {}{}".format(name, ("  " + detail) if detail else ""))
    else:
        FAILED.append(name)
        print("  [FAIL] {}{}".format(name, ("  " + detail) if detail else ""))


# ---------------------------------------------------------------- 假 CW2
def install_fake_cw2():
    """按 CW2 源码（src/core/plugin/*）造一个最小可用的宿主环境。"""
    src = types.ModuleType("src")
    src.__path__ = []
    core = types.ModuleType("src.core")
    core.__path__ = []
    plugin_mod = types.ModuleType("src.core.plugin")
    plugin_mod.__path__ = []
    bridge_mod = types.ModuleType("src.core.plugin.bridge")

    class CW2Plugin(object):
        def __init__(self, api):
            self.api = api
            self.PATH = Path()
            self.meta = {}
            self.pid = None

        def on_load(self):
            self.pid = self.meta.get("id")
            if self.pid:
                from src.core.plugin.bridge import PluginBackendBridge

                PluginBackendBridge.register_backend(self.pid, self)
                self.api.set_current_plugin(self)

        def on_unload(self):
            pass

    class PluginBackendBridge(object):
        registered = {}

        @staticmethod
        def register_backend(plugin_id, backend):
            PluginBackendBridge.registered[plugin_id] = backend

    plugin_mod.CW2Plugin = CW2Plugin
    plugin_mod.PluginAPI = object
    bridge_mod.PluginBackendBridge = PluginBackendBridge

    sys.modules["src"] = src
    sys.modules["src.core"] = core
    sys.modules["src.core.plugin"] = plugin_mod
    sys.modules["src.core.plugin.bridge"] = bridge_mod
    return CW2Plugin


class FakeUiAPI(object):
    def __init__(self):
        self.shortcuts = []

    def register_shortcut(self, shortcut_id, name, icon, action):
        self.shortcuts.append({
            "id": shortcut_id, "name": name, "icon": icon, "action": action,
        })
        return "com.mchuaihuai.classspeaker." + shortcut_id


class FakePluginAPI(object):
    def __init__(self):
        self.ui = FakeUiAPI()
        self.current = None

    def set_current_plugin(self, plugin):
        self.current = plugin


def load_entry():
    path = os.path.join(PLUGIN_DIR, "plugin.py")
    spec = importlib.util.spec_from_file_location("cw2_classspeaker_plugin", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["cw2_classspeaker_plugin"] = module
    spec.loader.exec_module(module)
    return module


def main():
    app = QApplication(sys.argv)
    plugin = None
    try:
        install_fake_cw2()
        module = load_entry()

        print("\n== 清单与入口（CW2 契约）==")
        # 防呆：CW2 副本必须是 PySide6，不能混进 PyQt5 的 import（否则 CW2 里一 import 就炸）
        import re

        pyqt_pattern = re.compile(r"^\s*(from|import)\s+PyQt5|pyqtSignal", re.M)
        offenders = []
        for current, _dirs, files in os.walk(PLUGIN_DIR):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(current, name)
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                if pyqt_pattern.search(text):
                    offenders.append(os.path.relpath(path, PLUGIN_DIR))
        check("CW2 副本里没有 PyQt5 import 残留", not offenders, str(offenders))

        with open(os.path.join(PLUGIN_DIR, "cwplugin.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        for field in ("id", "name", "version", "api_version", "entry", "author"):
            check("cwplugin.json 有 {}".format(field),
                  bool(manifest.get(field)), str(manifest.get(field)))
        check("entry 文件存在",
              os.path.isfile(os.path.join(PLUGIN_DIR, manifest["entry"])))
        check("api_version 是 PEP440 约束",
              manifest["api_version"].startswith(">="), manifest["api_version"])
        check("入口定义了 Plugin 类", hasattr(module, "Plugin"))

        print("\n== on_load / on_unload ==")
        api = FakePluginAPI()
        plugin = module.Plugin(api)
        plugin.meta = dict(manifest)          # 正常由加载器填
        plugin.on_load()
        app.processEvents()

        check("服务已启动", plugin.core is not None and plugin.core.server.running)
        check("教师端地址可用",
              plugin.core is not None and plugin.core.address.startswith("http://"),
              plugin.core.address if plugin.core else "")
        check("注册了设置快捷方式",
              len(api.ui.shortcuts) == 1, str(api.ui.shortcuts))
        if api.ui.shortcuts:
            shortcut = api.ui.shortcuts[0]
            check("快捷方式名称正确", shortcut["name"] == "教室小喇叭设置")
            check("快捷方式 action 可调用", callable(shortcut["action"]))
        check("插件自带托盘图标（右键即有「设置…」）",
              plugin.desktop is not None and plugin.desktop.use_tray is True,
              "show_tray_icon 默认 true")
        check("pid 已由 on_load 设置", plugin.pid == manifest["id"])

        print("\n== 设置窗口（PySide6）==")
        plugin.open_settings()
        app.processEvents()
        panel = plugin._settings
        check("设置窗口已创建", panel is not None and panel.isVisible())
        if panel is not None:
            check("有端口设置", panel.port_spin.value() == plugin.core.config.port)
            check("有语音播报开关", panel.tts_check is not None)
            check("有中英文声音下拉",
                  panel.tts_zh_combo.count() >= 1 and panel.tts_en_combo.count() >= 1)
            check("显示了教师端地址", "http" in panel.report_label.text())
            panel.close()

        print("\n== 弹窗（PySide6）==")
        plugin.core.inject_test_message("上课了，请回到座位。", "张老师")
        app.processEvents()
        check("消息进入队列", plugin.desktop.queue_count() == 1,
              "count={}".format(plugin.desktop.queue_count()))
        plugin.desktop._tick()
        popup = plugin.desktop.popup
        check("弹窗已创建", popup is not None)
        if popup is not None:
            flags = popup.windowFlags()
            check("无边框", bool(flags & Qt.FramelessWindowHint))
            check("置顶", bool(flags & Qt.WindowStaysOnTopHint))
            label = popup.findChild(QLabel, "content")
            check("正文正确",
                  label is not None and "上课了" in label.text())
            check("只有确认按钮",
                  popup.confirm_btn.text() == "确认收到"
                  and popup.findChild(QPushButton, "closeBtn") is None)
            popup.show()
            app.processEvents()
            popup.close()                    # 模拟 Alt+F4
            app.processEvents()
            check("未经确认关不掉", not popup._confirmed)
            popup.confirm()
            app.processEvents()
            messages = plugin.core.store.list_messages(limit=5)
            check("确认后写入回执",
                  messages and messages[0]["status"] == "received")

        print("\n== 卸载 ==")
        plugin.on_unload()
        app.processEvents()
        check("卸载后服务已停止",
              plugin.core is None or not plugin.core.server.running)
    finally:
        if plugin is not None and plugin.desktop is not None:
            try:
                plugin.desktop.shutdown()
            except Exception:
                pass
        shutil.rmtree(os.environ["CLASSSPEAKER_DATA_DIR"], ignore_errors=True)

    print("\n================ 结果 ================")
    print("通过 {} 项，失败 {} 项".format(len(PASSED), len(FAILED)))
    if FAILED:
        for name in FAILED:
            print(" - 失败：{}".format(name))
        return 1
    print("全部通过 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
