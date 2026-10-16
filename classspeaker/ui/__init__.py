# -*- coding: utf-8 -*-
"""教室小喇叭 —— 界面子包（PyQt5）。"""

from .desktop import SpeakerDesktop
from .popup import MessageBox
from .settings import (
    PluginSettings,
    SettingsDialog,
    SettingsPanel,
    is_plugin_mode,
    set_current_core,
    set_plugin_mode,
)

__all__ = [
    "SpeakerDesktop",
    "MessageBox",
    "SettingsDialog",
    "SettingsPanel",
    "PluginSettings",
    "set_current_core",
    "set_plugin_mode",
    "is_plugin_mode",
]
