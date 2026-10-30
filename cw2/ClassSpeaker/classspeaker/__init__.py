# -*- coding: utf-8 -*-
"""教室小喇叭 —— 核心逻辑包（纯标准库）。

包名刻意使用 classspeaker 而不是 core/ui，
避免与 Class Widgets 自带的 ui 目录等同名模块冲突。
"""

from .app import VERSION, SpeakerCore
from .config import Config
from .store import Store

__all__ = ["SpeakerCore", "Config", "Store", "VERSION"]
