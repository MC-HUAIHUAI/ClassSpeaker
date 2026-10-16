# -*- coding: utf-8 -*-
"""教室小喇叭 —— Class Widgets 插件包。

CW 的 PluginLoader 执行 `importlib.import_module("plugins.ClassSpeaker")`，
因此这个文件必须存在，并把 `Plugin`（必需）与 `Settings`（可选设置页）
暴露在包命名空间上：

    if hasattr(module, 'Settings'): ...module.Settings(plugin_path)...
    if hasattr(module, 'Plugin'):   ...module.Plugin(cw_contexts, method)...

少了这个文件，CW 会把本目录当成 PEP 420 命名空间包——
导入不报错、也找不到 Plugin，日志却照样打「加载插件成功」，插件实际不会被运行。
"""

from .main import (  # noqa: F401
    WIDGET_CODE,
    WIDGET_NAME,
    WIDGET_WIDTH,
    Plugin,
    Settings,
)

__all__ = ["Plugin", "Settings", "WIDGET_CODE", "WIDGET_NAME", "WIDGET_WIDTH"]
