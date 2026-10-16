# -*- coding: utf-8 -*-
"""教室小喇叭 —— 界面子包（PyQt5）。"""

from .desktop import SpeakerDesktop
from .popup import MessageBox
from .settings import PluginSettings, SettingsDialog, SettingsPanel, set_current_core

__all__ = [
    "SpeakerDesktop",
    "MessageBox",
    "SettingsDialog",
    "SettingsPanel",
    "PluginSettings",
    "set_current_core",
]
