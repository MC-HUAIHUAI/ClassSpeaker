# -*- coding: utf-8 -*-
"""Class Widgets 插件入口测试（不需要启动 Class Widgets）：

    set QT_QPA_PLATFORM=offscreen
    python tools/plugin_test.py

用假的 method 对象替换 CW 的插件接口，验证：
    * register_widget / change_widget_content 被正确调用
    * execute() 能起服务并弹窗
    * update() 每次心跳刷新小组件内容
"""
import importlib.util
import os
import shutil
import sys
import tempfile

# 让中文输出在任意控制台代码页下都不会崩（CI 上是英文环境）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 让测试用临时数据目录，绝不动正式配置与数据库
os.environ["CLASSSPEAKER_DATA_DIR"] = tempfile.mkdtemp(prefix="classspeaker_plugin_data_")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication  # noqa: E402

PASSED = []
FAILED = []


class FakeMethod(object):
    """模拟 Class Widgets 注入的 PluginMethod。"""

    def __init__(self):
        self.widgets = {}
        self.contents = []

    def register_widget(self, code, name, width):
        self.widgets[code] = {"name": name, "width": width}

    def get_widget(self, code):
        return self.widgets.get(code)

    def change_widget_content(self, code, title, content):
        self.contents.append((code, title, content))


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  [PASS] {}{}".format(name, ("  " + detail) if detail else ""))
    else:
        FAILED.append(name)
        print("  [FAIL] {}{}".format(name, ("  " + detail) if detail else ""))


def load_plugin_module():
    """按 Class Widgets 的方式加载插件。

    CW 执行的是 `importlib.import_module("plugins.<目录名>")`，
    也就是**把插件目录当包导入**，会执行 __init__.py ——
    这样才真正验证 CW 能不能在包上找到 Plugin / Settings。
    （缺 __init__.py 时导入不会报错，但找不到 Plugin，插件实际不会运行。）
    """
    package_name = "plugins.ClassSpeaker"
    parent = os.path.dirname(ROOT)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    # CW 里 <CW_HOME>/plugins 本身是个包（CW_HOME 在 sys.path 上），
    # 这里造一个空的父包，让相对导入能正常解析到 plugins.ClassSpeaker.*
    if "plugins" not in sys.modules:
        parent_spec = importlib.util.spec_from_loader(
            "plugins", loader=None, is_package=True
        )
        parent_module = importlib.util.module_from_spec(parent_spec)
        parent_module.__path__ = []
        sys.modules["plugins"] = parent_module

    spec = importlib.util.spec_from_file_location(
        package_name,
        os.path.join(ROOT, "__init__.py"),
        submodule_search_locations=[ROOT],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


def main():
    temp_dir = tempfile.mkdtemp(prefix="classspeaker_plugin_")
    app = QApplication(sys.argv)
    plugin = None
    try:
        module = load_plugin_module()
        print("\n== 插件包结构（CW 的加载前提）==")
        check("包导入后能拿到 Plugin", hasattr(module, "Plugin"))
        check("包导入后能拿到 Settings", hasattr(module, "Settings"))
        check("Plugin 可调用",
              callable(getattr(module, "Plugin", None)))

        print("\n== 插件加载 ==")
        method = FakeMethod()
        contexts = {"PLUGIN_PATH": temp_dir, "State": 1, "Current_Lesson": "语文"}
        plugin = module.Plugin(contexts, method)

        check("保存了 cw_contexts", plugin.cw_contexts == contexts)
        check("保存了 method", plugin.method is method)
        check("注册了小组件",
              module.WIDGET_CODE in method.widgets,
              str(method.widgets))
        check("小组件名称正确",
              method.widgets.get(module.WIDGET_CODE, {}).get("name") == module.WIDGET_NAME)

        print("\n== execute() ==")
        plugin.execute()
        app.processEvents()
        check("服务已启动", plugin.core is not None and plugin.core.server.running)
        check("小组件内容已刷新", len(method.contents) >= 1,
              method.contents[-1][2] if method.contents else "")
        check("小组件内容含访问地址",
              any("http://" in c[2] for c in method.contents))
        if plugin.core is not None:
            check("教师端地址可用", plugin.core.address.startswith("http://"),
                  plugin.core.address)
        check("插件模式托盘开关跟随配置（默认 true）",
              plugin.desktop is not None
              and plugin.desktop.use_tray is bool(plugin.core.config.get("show_tray_icon", True)))

        print("\n== CW 设置页 ==")
        settings = module.Settings(temp_dir)
        check("Settings 可用插件路径构造", settings is not None)
        check("设置页懒解析到了核心对象",
              settings.core is plugin.core)
        check("设置页能显示地址",
              "http" in settings.report_label.text(),
              settings.report_label.text().splitlines()[-1])
        settings.close()

        print("\n== update() 心跳 ==")
        before = len(method.contents)
        plugin.update({"PLUGIN_PATH": temp_dir, "State": 0})
        check("内容未变时不重复写入", len(method.contents) == before,
              "before={} after={}".format(before, len(method.contents)))

        plugin.core.inject_test_message("插件测试消息", "王老师")
        app.processEvents()
        plugin.desktop._tick()
        check("弹窗已显示", plugin.desktop.popup is not None)
        if plugin.desktop.popup is not None:
            popup = plugin.desktop.popup
            check("弹窗无边框",
                  bool(popup.windowFlags() & 0x00000800))  # Qt.FramelessWindowHint
            check("弹窗显示发送者", "王老师" in popup._title_text(),
                  popup._title_text())
            popup.confirm()
            app.processEvents()
            messages = plugin.core.store.list_messages(limit=5)
            check("确认后写入回执",
                  messages and messages[0]["status"] == "received")

        plugin.update({"PLUGIN_PATH": temp_dir, "State": 0})
        check("待确认数归零后内容会刷新",
              any("待确认 0 条" in c[2] for c in method.contents),
              method.contents[-1][2])
    finally:
        if plugin is not None and plugin.desktop is not None:
            plugin.desktop.shutdown()
        elif plugin is not None and plugin.core is not None:
            plugin.core.stop()
        shutil.rmtree(temp_dir, ignore_errors=True)

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
